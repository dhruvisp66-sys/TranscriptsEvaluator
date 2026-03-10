import os
import json
import soundfile as sf
from datasets import load_dataset

def extract_audio():
    # 1. Define the dataset details from your URL
    dataset_id = "leduckhai/MultiMed-ST"
    subset = "Chinese"
    split = "corrected.test"
    output_dir = "extracted_audio_chinese"

    # 2. Create the directory to save extracted audio files
    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading dataset '{dataset_id}', subset: '{subset}', split: '{split}'...")

    # 3. Load the specific split from the Hugging Face hub
    dataset = load_dataset(dataset_id, name=subset, split=split)

    print(f"Successfully loaded {len(dataset)} examples. Starting extraction...")

    # 4. Iterate over the dataset and extract the audio
    for i, item in enumerate(dataset):
        # Create a specific directory for the example (audio1, audio2, etc)
        example_dir = os.path.join(output_dir, f"audio{i+1}")
        os.makedirs(example_dir, exist_ok=True)
        
        # The 'audio' column automatically decodes the audio file into a numpy array
        audio_data = item.get("audio")
        
        if audio_data is None:
            print(f"Warning: No audio data found at index {i}. Skipping.")
            continue
        
        # Extract the numerical array and the sample rate
        audio_array = audio_data["array"]
        sample_rate = audio_data["sampling_rate"]
        
        # Determine a filename (use original filename if available, else use index)
        original_path = audio_data.get("path")
        
        if original_path and isinstance(original_path, str) and original_path.strip() != "":
            # Extract just the filename from the original path
            file_name = os.path.basename(original_path)
            # Ensure it ends with .wav
            if not file_name.lower().endswith('.wav'):
                file_name = f"{os.path.splitext(file_name)[0]}.wav"
        else:
            file_name = f"audio_{i+1}.wav"
            
        # Full path to save audio
        output_path = os.path.join(example_dir, file_name)
        
        # 5. Save the file using soundfile
        sf.write(output_path, audio_array, sample_rate)
        
        # Save metadata and transcript
        # We copy the entire item except the 'audio' array
        metadata = {k: v for k, v in item.items() if k != "audio"}
        
        metadata_path = os.path.join(example_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        # Print progress every 100 files
        if (i + 1) % 100 == 0:
            print(f"Extracted {i + 1} files...")

    print(f"Extraction complete! All audio files are saved in the '{output_dir}' directory.")

if __name__ == "__main__":
    extract_audio()