import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
import sys
import re

pdf_path = "Bank statement 2 High FOIR.pdf"
output_csv = "Bank statement 2 High FOIR_transactions.csv"

def is_amount(s):
    # Check if string looks like number e.g. 12,000.00
    cleaned = s.replace(',', '').replace('.', '')
    return cleaned.isdigit()

try:
    pages = convert_from_path(pdf_path)
except Exception as e:
    print(f"Error converting PDF: {e}")
    sys.exit(1)

all_rows = []
headers_found = False
col_boundaries = {}

for page_num, image in enumerate(pages):
    print(f"Processing Page {page_num + 1}")
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    n_boxes = len(data['text'])
    
    words = []
    for i in range(n_boxes):
        if int(data['conf'][i]) > 0:
            word = data['text'][i].strip()
            if word:
                words.append({
                    'text': word,
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })

    words.sort(key=lambda w: (w['top'], w['left']))
    
    lines = []
    if words:
        current_line = [words[0]]
        for word in words[1:]:
            last_word = current_line[-1]
            if abs(word['top'] - last_word['top']) < 15:
                current_line.append(word)
            else:
                lines.append(current_line)
                current_line = [word]
        lines.append(current_line)

    if not headers_found and page_num == 0:
        for line in lines:
            line_text = " ".join([w['text'] for w in line]).lower()
            if "date" in line_text and "narration" in line_text and "balance" in line_text:
                print(f"Found Header Line: {line_text}")
                header_map = {}
                for w in line:
                    txt = w['text'].lower()
                    for key in ['date', 'narration', 'debit', 'credit', 'balance']:
                        if key in txt and key not in header_map:
                            header_map[key] = w
                
                if 'debit' in header_map and 'credit' in header_map and 'balance' in header_map:
                    # Use Left edge of numeric columns as boundaries
                    # Narration ends 10px before Debit starts
                    col_boundaries['narration_end'] = header_map['debit']['left'] - 10
                    # Debit ends 10px before Credit starts
                    col_boundaries['debit_end'] = header_map['credit']['left'] - 10
                    # Credit ends 10px before Balance starts
                    col_boundaries['credit_end'] = header_map['balance']['left'] - 10
                    # Date ends... usually Date is width of date. 
                    # Let's say Date ends at Narration.left if found, or just hardcode?
                    # Narration header is Left aligned.
                    if 'narration' in header_map:
                         col_boundaries['date_end'] = header_map['narration']['left'] - 10
                    else:
                         col_boundaries['date_end'] = 200 # Fallback
                         
                    print(f"Boundaries: {col_boundaries}")
                    headers_found = True
                    continue 

    for line in lines:
        if not headers_found: continue
        line_txt = " ".join([w['text'] for w in line]).lower()
        if "date" in line_txt and "narration" in line_txt: continue
        if len(line) < 2: continue

        date_parts = []
        narration_parts = []
        debit_parts = []
        credit_parts = []
        balance_parts = []

        for w in line:
            cx = w['left'] + w['width']/2
            # Assign to columns
            if cx < col_boundaries.get('date_end', 0):
                date_parts.append(w['text'])
            elif cx < col_boundaries['narration_end']:
                narration_parts.append(w['text'])
            elif cx < col_boundaries['debit_end']:
                debit_parts.append(w['text'])
            elif cx < col_boundaries['credit_end']:
                credit_parts.append(w['text'])
            else:
                balance_parts.append(w['text'])
        
        # Post-processing: clean Debit/Credit if they contain non-numeric text
        # Move overlapping text to Narration
        
        def clean_money_col(parts, target_list):
            amt_parts = []
            text_parts = []
            for p in parts:
                if is_amount(p):
                    amt_parts.append(p)
                else:
                    text_parts.append(p)
            # Reconstruct
            return " ".join(text_parts), " ".join(amt_parts)

        deb_text, deb_amt = clean_money_col(debit_parts, debit_parts)
        cred_text, cred_amt = clean_money_col(credit_parts, credit_parts)
        
        real_narration = " ".join(narration_parts)
        if deb_text: real_narration += " " + deb_text
        if cred_text: real_narration += " " + cred_text
        
        row_data = {
            'Date': " ".join(date_parts),
            'Narration': real_narration.strip(),
            'Debit': deb_amt,
            'Credit': cred_amt,
            'Balance': " ".join(balance_parts)
        }
        
        # Validate Date format to filter garbage lines
        # simple regex dd/mm/yyyy
        if re.match(r'\d{2}/\d{2}/\d{4}', row_data['Date']):
             all_rows.append(row_data)

df = pd.DataFrame(all_rows)
print(f"Extracted {len(df)} transactions.")
df.to_csv(output_csv, index=False)
print("Saved to CSV.")
