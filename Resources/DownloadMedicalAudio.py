import os
import json
import soundfile as sf
from datasets import load_dataset

def main():
    # Base directory for the resources
    base_dir = "Dataset_Resources"
    os.makedirs(base_dir, exist_ok=True)
    
    # We will define the sources we want to pull from
    # Note: Finding long audio + Korean/Portuguese/Arabic + 100% verified English transcript
    # is currently a gap in open-source Hugging Face datasets. 
    # We will pull the highest quality verified Chinese dataset available (MultiMed-ST).
    
    tasks = [
        {
            "language": "Mandarin_Chinese",
            "dataset": "leduckhai/MultiMed-ST",
            "subset": "Chinese",
            "split": "corrected.test"
        }
        # Add more datasets if/when they become available on Hugging Face for Arabic, Korean, Portuguese
    ]

    for task in tasks:
        lang_dir = os.path.join(base_dir, task["language"])
        os.makedirs(lang_dir, exist_ok=True)
        
        print(f"Loading {task['language']} from {task['dataset']}...")
        try:
            dataset = load_dataset(task["dataset"], name=task["subset"], split=task["split"])
        except Exception as e:
            print(f"Failed to load dataset: {e}")
            continue
            
        print(f"Loaded {len(dataset)} examples for {task['language']}. Extracting...")
        
        for i, item in enumerate(dataset):
            # Create a specific directory for each audio conversation chunk
            example_dir = os.path.join(lang_dir, f"audio{i+1}")
            os.makedirs(example_dir, exist_ok=True)
            
            # --- AUDIO EXTRACTION ---
            audio_data = item.get("audio")
            if audio_data is not None:
                audio_array = audio_data["array"]
                sample_rate = audio_data["sampling_rate"]
                
                # Format audio filename
                original_path = audio_data.get("path")
                if original_path and isinstance(original_path, str) and original_path.strip() != "":
                    file_name = os.path.basename(original_path)
                    if not file_name.lower().endswith('.wav'):
                        file_name = f"{os.path.splitext(file_name)[0]}.wav"
                else:
                    file_name = f"audio_{i+1}.wav"
                    
                output_path = os.path.join(example_dir, file_name)
                sf.write(output_path, audio_array, sample_rate)
            
            # --- METADATA & TRANSCRIPT EXTRACTION ---
            metadata = {k: v for k, v in item.items() if k != "audio"}
            metadata_path = os.path.join(example_dir, "metadata.json")
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=4)
                
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1} files for {task['language']}...")

if __name__ == "__main__":
    main()
