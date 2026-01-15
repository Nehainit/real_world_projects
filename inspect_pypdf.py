from pypdf import PdfReader

reader = PdfReader("Bank statement 2 High FOIR.pdf")
print(f"Number of Pages: {len(reader.pages)}")

for i, page in enumerate(reader.pages):
    print(f"--- Page {i+1} ---")
    text = page.extract_text()
    if text:
        print(text[:500])  # Print first 500 chars
    else:
        print("[No text found]")
