"""
PDF/Image Table & OCR Extractor

Place PDFs or images into the `input_files/` folder, then run this script.
It will prompt you to choose a file and pages to extract, run text extraction
(if PDF contains text), otherwise OCR (Tesseract), cluster tokens into rows
and columns, save CSV(s) and page image(s) into `output/`.

Preserves page images (saved under output/images/) and adds a `page_image`
column in CSV pointing to the saved page image file.

Quick features:
- Interactive file selection or CLI args
- Multi-page selection (e.g. "1,3,5-7" or "all")
- Uses pdfplumber for text PDFs, falls back to pytesseract OCR for scanned PDFs
- DBSCAN clustering to infer columns (tune `x_eps` and `y_tol`)
- Saves CSV per page and a combined CSV per file

Practical tips (also included in README):
- Tune tolerances: `y_tol` and `x_eps` depend on PDF resolution and font sizes; test visually.
- Header detection: detect a header row (e.g., bigger font) to set column names.
- Post-processing: regex-based normalization for numeric fields, units, and merging broken cells.
- Use layout models: if heuristics fail, use specialized table-detection models (CascadeTabNet, TableNet, TableFormer) to detect cell polygons, then OCR each cell.
- Confidence filtering: use OCR confidences from `pytesseract.image_to_data` to ignore low-confidence tokens.
- Human-in-the-loop: for medical reports, add validation rules (value ranges) to flag suspicious parses.

Requirements: see requirements.txt. On Windows, install Poppler (for `pdf2image`) and Tesseract OCR
and add them to PATH (or pass their paths to the script).

"""

import os
import argparse
import sys
import shutil
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

# PDF / OCR libs
try:
    import pdfplumber
except Exception:
    pdfplumber = None
try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None
try:
    from PIL import Image
except Exception:
    Image = None
try:
    import pytesseract
    from pytesseract import Output
except Exception:
    pytesseract = None
    Output = None

from sklearn.cluster import DBSCAN


# -------- Utilities --------

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def parse_pages_spec(spec: str, n_pages: int):
    """Parse page specification like "1,3,5-7" or "all" into 0-based indices."""
    spec = spec.strip().lower()
    if spec == "all":
        return list(range(n_pages))
    pages = set()
    parts = [s.strip() for s in spec.split(",") if s.strip()]
    for p in parts:
        if "-" in p:
            a, b = p.split("-")
            a = int(a) - 1
            b = int(b) - 1
            pages.update(range(max(0, a), min(n_pages, b) + 1))
        else:
            idx = int(p) - 1
            if 0 <= idx < n_pages:
                pages.add(idx)
    return sorted(pages)


# -------- Extraction logic (text PDF) --------

def extract_table_from_words(words, y_tol=5, x_gap=50):
    """Take a list of words (dicts with x0,x1,top,bottom,text) and return a DataFrame."""
    if not words:
        return pd.DataFrame()
    # sort
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    # group into rows by y tolerance
    rows = []
    cur_row = []
    cur_top = None
    for w in words:
        top = w["top"]
        if cur_top is None or abs(top - cur_top) <= y_tol:
            cur_row.append(w)
            cur_top = top if cur_top is None else (cur_top + top) / 2.0
        else:
            rows.append(cur_row)
            cur_row = [w]
            cur_top = top
    if cur_row:
        rows.append(cur_row)

    # Detect columns by finding gaps in x positions
    all_x0 = sorted(set(w["x0"] for r in rows for w in r))
    boundaries = [0]
    for i in range(1, len(all_x0)):
        if all_x0[i] - all_x0[i-1] > x_gap:
            boundaries.append(all_x0[i])
    boundaries.append(float('inf'))
    n_cols = len(boundaries) - 1

    # For each row, assign words to columns
    table_rows = []
    for r in rows:
        row_cells = [""] * n_cols
        for w in r:
            x0 = w["x0"]
            for i in range(n_cols):
                if boundaries[i] <= x0 < boundaries[i+1]:
                    text = w.get("text", "").strip()
                    existing = row_cells[i]
                    row_cells[i] = (existing + " " + text).strip() if existing else text
                    break
        table_rows.append(row_cells)

    max_cols = max(len(r) for r in table_rows) if table_rows else 0
    normalized = [row + [""] * (max_cols - len(row)) for row in table_rows]
    df = pd.DataFrame(normalized)
    return df


# -------- Page processing --------

def render_page_image_from_pdf(pdf_path, page_index, dpi=200, poppler_path=None):
    """Render a single PDF page to a PIL Image using pdf2image."""
    if convert_from_path is None:
        raise RuntimeError("pdf2image not installed")
    # page numbers for convert_from_path are 1-based
    imgs = convert_from_path(pdf_path, dpi=dpi, first_page=page_index + 1, last_page=page_index + 1, poppler_path=poppler_path)
    if not imgs:
        raise RuntimeError("Failed to render page")
    return imgs[0]


def process_pdf_file(path: Path, pages, out_dir: Path, options):
    """Process a PDF file: for each page, attempt text extract with pdfplumber, otherwise OCR."""
    basename = path.stem
    images_out = out_dir / "images"
    ensure_dir(images_out)
    csvs = []

    # open pdfplumber if available
    plumb = None
    if pdfplumber is not None:
        try:
            plumb = pdfplumber.open(str(path))
        except Exception:
            plumb = None

    # get page count
    n_pages = None
    if plumb is not None:
        n_pages = len(plumb.pages)
    else:
        # we can try rendering to find pages
        if convert_from_path is not None:
            try:
                # this is a heavyweight check but works as fallback
                imgs = convert_from_path(str(path), first_page=1, last_page=1, dpi=10, poppler_path=options.get("poppler_path"))
                # if success, assume pages > 0; user provided explicit pages anyway
                n_pages = 1000  # a large number; parse_pages_spec will bound
            except Exception:
                n_pages = 1
        else:
            n_pages = 1

    for pidx in pages:
        print(f"Processing {path.name} page {pidx + 1}...")
        # render page image (always save page image)
        try:
            pil_img = render_page_image_from_pdf(str(path), pidx, dpi=options.get("dpi", 200), poppler_path=options.get("poppler_path"))
        except Exception as e:
            print("Warning: could not render page to image:", e)
            pil_img = None

        # save page image
        image_name = f"{basename}_page{pidx + 1}.png"
        image_path = images_out / image_name
        if pil_img is not None:
            pil_img.save(str(image_path))
            page_image_path = str(image_path)
        else:
            page_image_path = None

        # try pdfplumber text extraction
        df = None
        if plumb is not None:
            try:
                page = plumb.pages[pidx]
                # First try built-in table extraction
                tables = page.extract_tables()
                if tables:
                    # Assume the first table is the main one
                    table = tables[0]
                    df = pd.DataFrame(table)
                else:
                    # Fallback to heuristic
                    words = page.extract_words(extra_attrs=["size"])
                    if words:
                        df = extract_table_from_words(words, y_tol=options.get("y_tol", 5), x_gap=options.get("x_gap", 50))
            except Exception:
                df = None

        # fallback to OCR using pytesseract on rendered image
        if df is None:
            if pil_img is None:
                print("No page image to OCR; skipping page.")
                continue
            data = pytesseract.image_to_data(pil_img, output_type=Output.DICT)
            words = []
            for i, txt in enumerate(data["text"]):
                txt = str(txt).strip()
                if not txt:
                    continue
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                conf = float(data.get("conf", [])[i]) if "conf" in data and data.get("conf") else None
                words.append({"text": txt, "x0": x, "x1": x + w, "top": y, "bottom": y + h, "conf": conf})
            df = extract_table_from_words(words, y_tol=options.get("y_tol", 8), x_gap=options.get("x_gap", 50))

        # add page image path column to df (if not empty)
        if df is not None and not df.empty and page_image_path is not None:
            df.insert(0, "page_image", page_image_path)

        # save CSV per page
        out_csv = out_dir / f"{basename}_page{pidx + 1}.csv"
        if df is not None and not df.empty:
            df.to_csv(str(out_csv), index=False)
            csvs.append(out_csv)
            print(f"Saved CSV: {out_csv}")
        else:
            print(f"No table found on page {pidx + 1}")

        # extract embedded images
        if plumb is not None:
            try:
                page = plumb.pages[pidx]
                for img_idx, img in enumerate(page.images):
                    img_name = f"{basename}_page{pidx + 1}_img{img_idx}.png"
                    img_path = images_out / img_name
                    with open(str(img_path), 'wb') as f:
                        f.write(img['stream'].get_data())
                    print(f"Saved embedded image: {img_path}")
            except Exception as e:
                print(f"Warning: could not extract embedded images: {e}")

    # close pdfplumber
    if plumb is not None:
        plumb.close()

    # Optionally write combined CSV
    if csvs:
        combined = pd.concat([pd.read_csv(str(c)) for c in csvs], ignore_index=True, sort=False)
        combined_path = out_dir / f"{basename}_combined.csv"
        combined.to_csv(str(combined_path), index=False)
        print(f"Saved combined CSV: {combined_path}")


# -------- Image file processing (png/jpg) --------

def process_image_file(path: Path, pages, out_dir: Path, options):
    """For single images, `pages` is ignored; process the image as one page."""
    images_out = out_dir / "images"
    ensure_dir(images_out)
    basename = path.stem
    pil_img = Image.open(str(path))
    image_name = f"{basename}_image.png"
    image_path = images_out / image_name
    pil_img.save(str(image_path))

    data = pytesseract.image_to_data(pil_img, output_type=Output.DICT)
    words = []
    for i, txt in enumerate(data["text"]):
        txt = str(txt).strip()
        if not txt:
            continue
        x = data["left"][i]
        y = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]
        conf = float(data.get("conf", [])[i]) if "conf" in data and data.get("conf") else None
        words.append({"text": txt, "x0": x, "x1": x + w, "top": y, "bottom": y + h, "conf": conf})
    df = extract_table_from_words(words, y_tol=options.get("y_tol", 8), x_gap=options.get("x_gap", 50))
    if df is not None and not df.empty:
        df.insert(0, "page_image", str(image_path))
        out_csv = out_dir / f"{basename}.csv"
        df.to_csv(str(out_csv), index=False)
        print(f"Saved CSV: {out_csv}")


# -------- CLI / Interactive --------

def list_input_files(input_dir: Path):
    files = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")])
    return files


def main():
    parser = argparse.ArgumentParser(description="Extract tabular data from PDFs/images (heuristic OCR + layout clustering)")
    parser.add_argument("--input", help="Path to input PDF or image (optional: will prompt if not given)")
    parser.add_argument("--pages", default="1", help='Pages to process (1-based, e.g. "1,3,5-7" or "all"). Default=1')
    parser.add_argument("--output", default="output", help="Output folder (default: output)")
    parser.add_argument("--input-dir", default="input_files", help="Folder where you drop files (default: input_files)")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI for page images")
    parser.add_argument("--poppler-path", default=None, help="Optional path to poppler bin (Windows)")
    parser.add_argument("--tesseract-path", default=None, help="Optional path to tesseract exe (Windows)")
    parser.add_argument("--y-tol", type=float, default=6.0)
    parser.add_argument("--x-gap", type=float, default=50.0)
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    ensure_dir(input_dir)
    out_dir = Path(args.output)
    ensure_dir(out_dir)

    if args.tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_path

    # choose file
    input_path = None
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print("Input file does not exist:", input_path)
            sys.exit(1)
    else:
        files = list_input_files(input_dir)
        if not files:
            print(f"No PDF/image files in {input_dir}. Put files in that folder or pass --input path.")
            sys.exit(1)
        print("Input files in", input_dir)
        for i, f in enumerate(files, start=1):
            print(f"{i}. {f.name}")
        sel = input("Choose file number (or 0 to quit): ")
        try:
            si = int(sel)
            if si <= 0:
                print("Aborted")
                sys.exit(0)
            input_path = files[si - 1]
        except Exception:
            print("Invalid selection")
            sys.exit(1)

    # determine page indices
    pages_spec = args.pages
    if input_path.suffix.lower() == ".pdf":
        # if pdfplumber available, get proper page count
        n_pages = None
        if pdfplumber is not None:
            with pdfplumber.open(str(input_path)) as p:
                n_pages = len(p.pages)
        else:
            n_pages = 1000
        pages = parse_pages_spec(pages_spec, n_pages)
    else:
        pages = [0]

    options = {"dpi": args.dpi, "poppler_path": args.poppler_path, "y_tol": args.y_tol, "x_gap": args.x_gap}

    # process
    if input_path.suffix.lower() == ".pdf":
        process_pdf_file(input_path, pages, out_dir, options)
    else:
        process_image_file(input_path, pages, out_dir, options)

    print("Extraction complete. Starting web UI...")
    import subprocess
    import sys
    subprocess.Popen([sys.executable, 'web_ui.py'])


if __name__ == '__main__':
    main()
