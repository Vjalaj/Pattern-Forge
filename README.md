# Table & OCR Extractor

This repository provides a single Python script `extractor.py` to extract table-like
information from PDFs and images (e.g., medical blood test reports) when the table
has no strict Excel-style gridlines.

Features
- Uses `pdfplumber` for text PDFs; falls back to Tesseract OCR (`pytesseract`) for scanned pages.
- Groups text tokens into rows by vertical proximity and clusters x-centers into inferred columns.
- Saves per-page CSVs and a combined CSV per PDF; saves page images under `output/images/`.
- Preserves page images and includes the page image path in CSV rows.

Quick Setup (Windows example)
1. Clone the repo:

```powershell
git clone https://github.com/Vjalaj/Pattern-Forge.git
cd Pattern_Forge
```

2. Create and activate a venv (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Install system dependencies:
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
  - On Windows, install the installer and add `C:\Program Files\Tesseract-OCR` to PATH.
- Poppler (for `pdf2image`): download Windows binaries and add `poppler\bin` to PATH.

4. Place your PDF(s) or image(s) into the `input_files/` folder.

Usage
- Interactive (recommended):

```powershell
python extractor.py
```

The script will list files in `input_files/` and prompt you to choose one and the pages to extract.

- Command-line:

```powershell
python extractor.py --input input_files\report.pdf --pages "1,3,5-7" --output output --dpi 300 --poppler-path "C:\path\to\poppler\bin" --tesseract-path "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Notes & Tips
- Tune tolerances: `y_tol` and `x_eps` depend on PDF resolution and font sizes; test visually.
- Header detection: detect a header row (e.g., bigger font) to set column names.
- Post-processing: regex-based normalization for numeric fields, units, and merging broken cells.
- Use layout models: if heuristics fail, use specialized table-detection models (CascadeTabNet, TableNet, TableFormer) to detect cell polygons, then OCR each cell.
- Confidence filtering: use OCR confidences from `pytesseract.image_to_data` to ignore low-confidence tokens.
- Human-in-the-loop: for medical reports, add validation rules (value ranges) to flag suspicious parses.

Output
- Per-page CSVs are saved in `output/` (e.g., `report_page1.csv`).
- A combined CSV is saved as `report_combined.csv`.
- Page images are saved in `output/images/` and linked from the CSV `page_image` column.

If you'd like, I can:
- Run this on a sample file you upload and show results.
- Add a small GUI or web UI for easier review/corrections.
