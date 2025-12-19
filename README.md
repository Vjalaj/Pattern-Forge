# PDF Table Extractor: Because Who Has Time for Manual Copy-Paste?

Ever stared at a PDF with a table that's sneakier than a cat burglar? This tool extracts tabular data from PDFs and images like a boss, using OCR when needed. Built with love, frustration, and way too many Stack Overflow tabs.

I used AI, Google, and YouTube to cobble this together, and I'm only uploading to GitHub months later to clean up the mess. Enjoy!

## Features
- Extracts tables from text PDFs using `pdfplumber` (fast and accurate).
- Falls back to Tesseract OCR for scanned PDFs or images.
- Heuristic clustering to infer columns from unstructured layouts.
- Saves CSVs per page + combined, plus embedded/page images.
- Web UI for easy review and extraction (no more command-line nightmares).
- Auto-starts the web UI after extraction—because laziness is a feature.

## Quick Setup (Windows, because why not?)
1. Clone this repo (or don't, I'm not your boss):
   ```powershell
   git clone https://github.com/Vjalaj/Pattern-Forge.git
   cd Pattern_Forge
   ```

2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Install system deps (don't skip, or it'll cry):
   - **Tesseract OCR**: Download from [here](https://github.com/tesseract-ocr/tesseract), install, and add `C:\Program Files\Tesseract-OCR` to PATH.
   - **Poppler** (for PDF images): Grab Windows binaries and add `poppler\bin` to PATH.

4. Drop your PDFs/images into `input_files/`.

## Usage
- **Command-line** (for the brave):
  ```powershell
  python extractor.py --input input_files\your_file.pdf --pages "1,3-5"
  ```
  It extracts and auto-launches the web UI at http://localhost:5000.

- **Web UI** (the fun way):
  ```powershell
  python web_ui.py
  ```
  Select file, pages, extract. View CSVs as tables, download images. Boom!

## Output
- `output/*.csv`: Per-page and combined CSVs.
- `output/images/`: Page renders and extracted embedded images.
- CSVs include `page_image` column linking to saved images.

## Tips & Tricks
- Tune `x_eps` (default 10) for column detection—lower for tighter tables.
- For medical reports, add validation rules post-extraction.
- If tables are wonky, try advanced models like CascadeTabNet.
- Confidence filtering: OCR results have confidences; filter low ones.

## Requirements
See `requirements.txt`. Needs Python 3.8+, Flask for UI, etc.

## Contributing
PRs welcome, but don't break it. I used AI to build this, so bugs are expected.

## License
MIT, because sharing is caring. Use at your own risk—I'm not liable if your PDF explodes.
```

Review Results
- Run the web UI to review CSVs and images, and to extract new files:

```powershell
python web_ui.py
```

Then open http://localhost:5000 in your browser. Select a PDF from the dropdown, enter pages, and click Extract. View the resulting CSVs as tables and downloaded images.

Notes & Tips
- Tune tolerances: `y_tol` and `x_eps` depend on PDF resolution and font sizes; test visually. For multi-column tables, try smaller `x_eps` (e.g., 10-15) to detect more columns.
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