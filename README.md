# Bank Statement Extractor

A robust tool to extract transaction data from scanned/image-based bank statement PDFs.

## Setup

1. Install system dependencies:
   - **Poppler** (for PDF conversion): `brew install poppler` (Mac)
   - **Tesseract** (for OCR): `brew install tesseract` (Mac)

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Place your PDF file in the project directory (default: `Bank statement 2 High FOIR.pdf`).
2. Run the extraction script:
   ```bash
   python3 extract_statement.py
   ```
3. The extracted data will be saved to `Bank statement 2 High FOIR_transactions.csv`.

## Features

- **OCR-based Extraction**: Handles image-only PDFs.
- **Intelligent Alignment**: Dynamically finds columns and correctly places amounts.
- **Smart Cleanup**: Separates text from numeric columns (e.g. moves "NO 402" from Debit column to Narration).
