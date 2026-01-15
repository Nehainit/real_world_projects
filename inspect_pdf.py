import pdfplumber

pdf_path = "Bank statement 2 High FOIR.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        
        print("--- Text ---")
        print(page.extract_text())
        
        print("\n--- Tables ---")
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                print(row)
