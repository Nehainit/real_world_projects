import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
import sys

pdf_path = "Bank statement 2 High FOIR.pdf"

# Convert PDF to images
try:
    pages = convert_from_path(pdf_path)
except Exception as e:
    print(f"Error converting PDF: {e}")
    sys.exit(1)

all_rows = []

# Column Headers usually found in first page
# We will detect them dynamically or hardcode relative positions if dynamic fails?
# Let's try dynamic first.
headers_found = False
col_boundaries = {}

for page_num, image in enumerate(pages):
    print(f"Processing Page {page_num + 1}")
    
    # Get data
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    n_boxes = len(data['text'])
    
    # Organize words by line (using top/height)
    # We will group words that are on the same visual line (similar 'top')
    
    words = []
    for i in range(n_boxes):
        if int(data['conf'][i]) > 0: # filter out weak confidence?
            word = data['text'][i].strip()
            if word:
                words.append({
                    'text': word,
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })

    # Sort words by top (y) then left (x)
    words.sort(key=lambda w: (w['top'], w['left']))
    
    # Cluster lines
    lines = []
    if words:
        current_line = [words[0]]
        for word in words[1:]:
            # If vertical overlap is significant or top is very close
            last_word = current_line[-1]
            # Simple line merging: if top difference is small (< height/2)
            if abs(word['top'] - last_word['top']) < 15: # 15px threshold
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]
        lines.append(current_line)

    # Detect Headers in Page 1
    if not headers_found and page_num == 0:
        for line in lines:
            line_text = " ".join([w['text'] for w in line]).lower()
            if "date" in line_text and "narration" in line_text and "balance" in line_text:
                print(f"Found Header Line: {line_text}")
                # Determine boundaries
                # Simple logic: Find 'date', 'narration', 'debit', 'credit', 'balance' words in this line
                header_map = {}
                for w in line:
                    txt = w['text'].lower()
                    if 'date' in txt: header_map['date'] = w
                    elif 'narration' in txt: header_map['narration'] = w
                    elif 'debit' in txt: header_map['debit'] = w
                    elif 'credit' in txt: header_map['credit'] = w
                    elif 'balance' in txt: header_map['balance'] = w
                
                # If we found enough headers, define boundaries
                if 'debit' in header_map and 'credit' in header_map:
                    # Separation points
                    # Narration ends where Debit begins (minus some buffer) or at specific X
                    # Debit/Credit split = (Debit.right + Credit.left) / 2 isn't great if headers are centered.
                    # Best: Debit starts at Debit.left - margin?
                    # Let's use midpoints between header centers
                    
                    def get_center(w): return w['left'] + w['width']/2
                    
                    d_c = get_center(header_map['date'])
                    n_c = get_center(header_map['narration'])
                    deb_c = get_center(header_map['debit'])
                    cred_c = get_center(header_map['credit'])
                    bal_c = get_center(header_map['balance'])
                    
                    col_boundaries['date_end'] = (d_c + n_c) / 2
                    col_boundaries['narration_end'] = (n_c + deb_c) / 2 
                    col_boundaries['debit_end'] = (deb_c + cred_c) / 2
                    col_boundaries['credit_end'] = (cred_c + bal_c) / 2
                    
                    # Refine Narration end / Debit start
                    # Narration usually goes until Debit column.
                    # Debit column data is numbers, usually right aligned to 'Debit' header or centered.
                    # Let's try strict midpoints for now.
                    print(f"Boundaries: {col_boundaries}")
                    headers_found = True
                    continue # Skip header row in data
                else:
                    print("Could not find all headers in header candidate line.")

    # Process Data Rows
    for line in lines:
        if not headers_found: continue
        
        # Skip if line is the header itself (already skipped above hopefully, but check)
        line_txt = " ".join([w['text'] for w in line]).lower()
        if "date" in line_txt and "narration" in line_txt: continue
        
        # Skip empty or noise
        if len(line) < 2: continue

        # Extract fields
        date_parts = []
        narration_parts = []
        debit_parts = []
        credit_parts = []
        balance_parts = []

        for w in line:
            cx = w['left'] + w['width']/2
            # date < date_end
            # date_end < narration < narration_end
            # narration_end < debit < debit_end
            # debit_end < credit < credit_end
            # credit_end < balance
            
            if cx < col_boundaries.get('date_end', 0): # Wait, date_end should be around Date|Narration split
                # Actually, date is usually first column.
                # Use boundaries:
                # | Date | Narration | Debit | Credit | Balance |
                pass

            if cx < col_boundaries['date_end']: # This boundary is Date|Narration midpoint? No, (d+n)/2 might be too far right if narration is long?
                 # Wait, Narration is usually Left Aligned. Date is Left Aligned.
                 # (Date_Center + Narration_Center)/2 might actally cut into Narration if Narration is close?
                 # Actually, Date is fixed width roughly.
                 # Let's use strict cutoffs based on previous visual inspection or just the midpoint.
                 date_parts.append(w['text'])
            elif cx < col_boundaries['narration_end']:
                narration_parts.append(w['text'])
            elif cx < col_boundaries['debit_end']:
                debit_parts.append(w['text'])
            elif cx < col_boundaries['credit_end']:
                credit_parts.append(w['text'])
            else:
                balance_parts.append(w['text'])
        
        # Construct row
        row_data = {
            'Date': " ".join(date_parts),
            'Narration': " ".join(narration_parts),
            'Debit': " ".join(debit_parts),
            'Credit': " ".join(credit_parts),
            'Balance': " ".join(balance_parts)
        }
        
        # Only add valid rows (must have Date or Balance or something substantial)
        if row_data['Date'] or row_data['Debit'] or row_data['Credit']:
            all_rows.append(row_data)

# Export
df = pd.DataFrame(all_rows)
print("\n--- Extracted Data ---")
print(df.to_string())
df.to_csv("ocr_output.csv", index=False)
