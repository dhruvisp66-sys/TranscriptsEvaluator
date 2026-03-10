import os
import shutil
import pandas as pd
import json

def process_audio_files():
    base_resources_dir = "Resources"
    educational_dir = os.path.join(base_resources_dir, "Educational")
    conversational_dir = os.path.join(base_resources_dir, "Conversational")
    
    os.makedirs(educational_dir, exist_ok=True)
    os.makedirs(conversational_dir, exist_ok=True)

    # Note: Using excel mapping - many files have empty Observations. 
    # Example logic: if we see words like 'error', 'does not contain any conversational', 
    # 'only general conversation', or 'explanation' we might flag differently,
    # but the simplest explicit mapping or name check will be used.
    
    folders_to_scan = ['KoreanAUDIO', 'MandarinAUDIO', 'CantoneseAUDIO']
    
    excel_file = "Multilingual Files evaluation.xlsx"
    xl = pd.read_excel(excel_file, sheet_name=None)
    
    # Pre-build a lowercased filename mapping to observations / reasons
    file_mapping = {}
    for sheet_name, df in xl.items():
        if sheet_name in ['Korean', 'Mandarin', 'Cantonese', 'SA', 'AE']:
            col_name = 'File Name' if 'File Name' in df.columns else ('Audio File Name' if 'Audio File Name' in df.columns else None)
            if col_name:
                for idx, row in df.iterrows():
                    if pd.notna(row[col_name]):
                        fname = str(row[col_name]).strip().lower()
                        obs = str(row['Observations']).lower() if 'Observations' in df.columns and pd.notna(row['Observations']) else ""
                        reason = str(row['Reason for appointment']).lower() if 'Reason for appointment' in df.columns and pd.notna(row['Reason for appointment']) else ""
                        
                        file_mapping[fname] = {'obs': obs, 'reason': reason}
    
    # We will traverse the specified folders and classify
    for folder in folders_to_scan:
        if not os.path.exists(folder):
            continue
            
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith('.mp3') or file.endswith('.wav'):
                    file_path = os.path.join(root, file)
                    file_lower = file.lower()
                    file_base = os.path.splitext(file_lower)[0]
                    
                    # 1. Use existing folder structure hints (since they were manually placed originally)
                    # But the prompt says "ignore the dissection in the subfolders. folllow excel sheet evaluation or your own analysis"
                    
                    is_educational = False
                    
                    # 2. Check Excel mapping (matching by .mp3 or by base name containing the UUID)
                    # The excel files often have .mp3 in their name or just the uuid.
                    # As a heuristic, if any filename in excel is a substring of our physical file, or vice versa
                    matched_info = None
                    for xl_name, info in file_mapping.items():
                        if xl_name in file_lower or file_base in xl_name:
                            matched_info = info
                            break
                    
                    if matched_info:
                        combined_text = matched_info['obs'] + " " + matched_info['reason']
                        # Identify educational/lecture vs conversational
                        if any(keyword in combined_text for keyword in ['error', 'does not contain any conversation', 'explanation regarding', 'educational', 'monologue']):
                            is_educational = True
                    else:
                        # Fallback heuristic: 
                        # "educational" subfolder name in the path if no excel mapping was found
                        if 'educational' in root.lower():
                            is_educational = True
                            
                    
                    # Copy to appropriate directory
                    target_dir = educational_dir if is_educational else conversational_dir
                    target_path = os.path.join(target_dir, file)
                    
                    # To avoid naming collisions from different folders
                    if os.path.exists(target_path):
                        target_path = os.path.join(target_dir, f"{folder}_{file}")
                        
                    shutil.copy2(file_path, target_path)
                    print(f"Copied {file} -> {'Educational' if is_educational else 'Conversational'}")

if __name__ == "__main__":
    process_audio_files()
