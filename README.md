# PDF Table Extractor: Because Who Has Time for Manual Copy-Paste?

Ever stared at a PDF with a table that's sneakier than a cat burglar? Tired of wrestling with documents that look like they were designed by a committee of caffeinated interns? This tool extracts tabular data from PDFs and images like a boss, using OCR when needed. Built with love, frustration, and way too many Stack Overflow tabs.

I used AI, Google, and YouTube to cobble this together, and I'm only uploading to GitHub months later to clean up the mess. Enjoy—may it save you from PDF purgatory!

## Features
- Extracts tables from text PDFs using pdfplumber (fast and accurate—because speed matters).
- Falls back to Tesseract OCR for scanned PDFs or images (when your PDF decides to play hard-to-get).
- Heuristic clustering to infer columns from unstructured layouts (magic, but not really).
- Saves CSVs per page + combined, plus embedded/page images (hoarders rejoice).
- Web UI for easy review and extraction (no more command-line nightmares—GUI for the win).
- Auto-starts the web UI after extraction—because laziness is a feature, and we're all about efficiency.

## Quick Setup (Windows, because why not?)
Clone this repo (or don't):

```bash
git clone https://github.com/Vjalaj/Pattern-Forge.git
cd Pattern_Forge
```

Create a virtual environment (optional, but highly recommended—don't let your global Python turn into a junk drawer!):

```powershell
python -m venv venv  # Or whatever floats your boat, like 'env' or 'my_super_env'
.\venv\Scripts\Activate.ps1
```

Activate and install deps (because setup isn't complete until you do this dance):

```powershell

pip install -r requirements.txt
```

Install system deps (seriously, don't skip—the tool will throw a tantrum if you do):

- Tesseract OCR: Download from [here](https://tesseract-ocr.github.io/tessdoc/Installation.html), install, and add `C:\Program Files\Tesseract-OCR` to PATH. (It's the official spot—easier than hunting for buried treasure.)
- Poppler (for PDF images): Grab Windows binaries and add `poppler\bin` to PATH. (Because PDFs sometimes hide their images like shy bride.)

Drop your PDFs/images into `input_files/`. (Pro tip: Name them something memorable, or chaos ensues.)

## Usage
### Command-line (for the brave):
```powershell
python extractor.py --input input_files\your_file.pdf --pages "1,3-5"
```

It extracts and auto-launches the web UI at http://localhost:5000. (Boom—extraction without the drama.)

### Web UI (the fun way):
```powershell
python web_ui.py
```

Select file, pages, extract. View CSVs as tables, download images. Boom! (Even your grandma could use this.)

## Output
- `output/*.csv`: Per-page and combined CSVs (your data, neatly packaged).
- `output/images/`: Page renders and extracted embedded images (visual aids for the win).
- CSVs include `page_image` column linking to saved images (because context is key).

## Tips & Tricks
- Tune `x_eps` (default 10) for column detection—lower for tighter tables (think Goldilocks: not too loose, not too tight).
- For medical reports, add validation rules post-extraction (because doctors hate bad data).
- If tables are wonky, try advanced models like CascadeTabNet (when heuristics go on vacation).
- Confidence filtering: OCR results have confidences; filter low ones (garbage in, garbage out—avoid the trash).

## Requirements
See `requirements.txt`. Needs Python 3.8+, Flask for UI, etc. (The usual suspects.)

## Contributing
PRs welcome, but don't break it. I used AI to build this, so bugs are expected. (We're all human... mostly.)

## License
MIT, because sharing is caring. Use at your own risk—I'm not liable if your PDF explodes. (But seriously, back up your files.)

## Review Results
- Run the web UI to review CSVs and images, and to extract new files:

```powershell
python web_ui.py
```

Then open http://localhost:5000 in your browser. Select a PDF from the dropdown, enter pages, and click Extract. View the resulting CSVs as tables and downloaded images. (It's like Netflix, but for data.)

## Notes & Tips
- Tune tolerances: `y_tol` and `x_eps` depend on PDF resolution and font sizes; test visually. For multi-column tables, try smaller `x_eps` (e.g., 10-15) to detect more columns (precision is your friend).
- Header detection: detect a header row (e.g., bigger font) to set column names (because labels matter).
- Post-processing: regex-based normalization for numeric fields, units, and merging broken cells (clean up the mess).
- Use layout models: if heuristics fail, use specialized table-detection models (CascadeTabNet, TableNet, TableFormer) to detect cell polygons, then OCR each cell (bring out the big guns).
- Confidence filtering: use OCR confidences from `pytesseract.image_to_data` to ignore low-confidence tokens (quality over quantity).
- Human-in-the-loop: for medical reports, add validation rules (value ranges) to flag suspicious parses (trust, but verify).

## Output
- Per-page CSVs are saved in `output/` (e.g., `report_page1.csv`—one file per page, like chapters in a book).
- A combined CSV is saved as `report_combined.csv` (all your data in one happy place).
- Page images are saved in `output/images/` and linked from the CSV `page_image` column (visual proof for skeptics).
```