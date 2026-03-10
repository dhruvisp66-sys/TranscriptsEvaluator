import pandas as pd
import json
import math

excel_file = "Multilingual Files evaluation.xlsx"
out = {}
for sheet in ['Cantonese', 'Mandarin', 'Korean', 'Portuguese']:
    df = pd.read_excel(excel_file, sheet_name=sheet)
    col_name = 'File Name' if 'File Name' in df.columns else ('Audio File Name' if 'Audio File Name' in df.columns else None)
    
    records = []
    if col_name:
        for idx, row in df.iterrows():
            if pd.notna(row[col_name]):
                fname = str(row[col_name]).strip()
                obs = str(row['Observations']) if 'Observations' in df.columns and pd.notna(row['Observations']) else ""
                records.append({"File Name": fname, "Observations": obs})
    out[sheet] = records

with open("examine_sheets.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
