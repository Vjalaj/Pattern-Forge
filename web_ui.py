from flask import Flask, render_template_string, send_from_directory, url_for, request, redirect
import pandas as pd
import os
from pathlib import Path
import subprocess
import sys

app = Flask(__name__)

OUTPUT_DIR = Path("output")
IMAGES_DIR = OUTPUT_DIR / "images"
INPUT_DIR = Path("input_files")

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)

def check_tesseract():
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

tesseract_available = check_tesseract()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_file = request.form.get('pdf_file')
        pages = request.form.get('pages', 'all')
        if selected_file:
            # Run extraction
            cmd = [sys.executable, 'extractor.py', '--input', str(INPUT_DIR / selected_file), '--pages', pages]
            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                return f"Error running extraction: {e}. Make sure Tesseract OCR is installed and in PATH for image processing.", 500
            return redirect(url_for('index'))
    
    input_files = [f.name for f in INPUT_DIR.iterdir() if f.suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff')]
    csv_files = [f for f in OUTPUT_DIR.iterdir() if f.suffix == '.csv' and 'combined' not in f.name]
    combined_files = [f for f in OUTPUT_DIR.iterdir() if f.suffix == '.csv' and 'combined' in f.name]
    image_files = [f for f in IMAGES_DIR.iterdir() if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Table Extractor</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                padding: 30px;
            }
            h1 {
                text-align: center;
                color: #4a5568;
                margin-bottom: 30px;
            }
            form {
                background: #f7fafc;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                border: 1px solid #e2e8f0;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
                color: #2d3748;
            }
            select, input[type="text"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #cbd5e0;
                border-radius: 5px;
                font-size: 16px;
                margin-bottom: 15px;
            }
            input[type="submit"] {
                background: #3182ce;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                transition: background 0.3s;
            }
            input[type="submit"]:hover {
                background: #2c5282;
            }
            h2 {
                color: #2d3748;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 10px;
                margin-top: 40px;
            }
            .file-list {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 15px;
            }
            .file-list a {
                display: block;
                padding: 15px;
                background: #edf2f7;
                text-decoration: none;
                color: #2d3748;
                border-radius: 5px;
                transition: background 0.3s;
                border: 1px solid #e2e8f0;
            }
            .file-list a:hover {
                background: #e2e8f0;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
                background: white;
            }
            th, td {
                border: 1px solid #e2e8f0;
                padding: 12px;
                text-align: left;
            }
            th {
                background: #f7fafc;
                font-weight: 600;
            }
            img {
                max-width: 100%;
                height: auto;
                border-radius: 5px;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #3182ce;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PDF Table Extractor</h1>
            {% if not tesseract_available %}
            <div style="background: #fed7d7; color: #c53030; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
                Warning: Tesseract OCR is not installed. Image processing will fail. Please install Tesseract and add to PATH.
            </div>
            {% endif %}
            <form method="post">
                <label for="input_file">Select File (PDF or Image):</label>
                <select name="pdf_file" id="input_file">
                    {% for file in input_files %}
                        <option value="{{ file }}">{{ file }}</option>
                    {% endfor %}
                </select>
                <label for="pages">Pages (for PDFs, e.g., 1,3-5 or all; ignored for images):</label>
                <input type="text" name="pages" id="pages" value="all">
                <input type="submit" value="Extract Tables & Images">
            </form>
            <h2>Extracted CSVs</h2>
            <div class="file-list">
                {% for file in csv_files %}
                    <a href="{{ url_for('view_csv', filename=file.name) }}">{{ file.name }}</a>
                {% endfor %}
            </div>
            <h2>Combined CSVs</h2>
            <div class="file-list">
                {% for file in combined_files %}
                    <a href="{{ url_for('view_csv', filename=file.name) }}">{{ file.name }}</a>
                {% endfor %}
            </div>
            <h2>Extracted Images</h2>
            <div class="file-list">
                {% for file in image_files %}
                    <a href="{{ url_for('serve_image', filename=file.name) }}">{{ file.name }}</a>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """, input_files=input_files, csv_files=csv_files, combined_files=combined_files, image_files=image_files, tesseract_available=tesseract_available)

@app.route('/csv/<filename>')
def view_csv(filename):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        return "File not found", 404
    df = pd.read_csv(filepath)
    # Convert to HTML table
    table_html = df.to_html(index=False, escape=False)
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ filename }}</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                padding: 30px;
            }
            h1 {
                text-align: center;
                color: #4a5568;
                margin-bottom: 30px;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
                background: white;
            }
            th, td {
                border: 1px solid #e2e8f0;
                padding: 12px;
                text-align: left;
            }
            th {
                background: #f7fafc;
                font-weight: 600;
            }
            img {
                max-width: 100%;
                height: auto;
                border-radius: 5px;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #3182ce;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{{ filename }}</h1>
            <a class="back-link" href="{{ url_for('index') }}">← Back to Index</a>
            {{ table_html | safe }}
        </div>
    </body>
    </html>
    """, filename=filename, table_html=table_html)

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

if __name__ == '__main__':
    app.run(use_reloader=False, threaded=False)
