import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from the .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class ASREvaluator:
    def __init__(self, model_provider="gemini"):
        self.model_provider = model_provider
        
        if self.model_provider == "gemini":
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            
    def evaluate(self, audio_file_path, transcript_text):
        if self.model_provider == "gemini":
            return self._evaluate_gemini(audio_file_path, transcript_text)
        else:
            return {"error": f"Model provider {self.model_provider} is not fully implemented for audio native yet."}

    def _evaluate_gemini(self, audio_file_path, transcript_text):
        uploaded_file = None
        try:
            # Upload the audio file to Gemini File API
            uploaded_file = self.client.files.upload(file=audio_file_path)
            
            # Wait a few seconds for file to be processed by Google APIs
            time.sleep(3)
            
            prompt = f"""
You are an expert ASR (Automatic Speech Recognition) and medical translation evaluation judge.
You are provided with an original audio file (which may be in any language) and the generated English transcript for this audio.

Target Transcript to Evaluate:
\"\"\"
{transcript_text}
\"\"\"

Your task is to:
1. Listen to the audio natively to understand its language, speakers (count, gender), and audio quality.
2. Evaluate the accuracy of the generated English transcript against the original audio.
3. Be EXTREMELY STRICT about medical terminology and clinical safety. Check explicitly for:
   - Numbers (e.g., dosages like 50mg vs 15mg).
   - Confusables (e.g., hypo- vs hyper-, hypotension vs hypertension).
   - Accurate medicine names and diagnoses.
4. Extract medical Named Entities (NER) from the audio, map them to timestamps, and grade if the ASR captured them correctly.
5. Create a corrected transcript with timestamps.

Calculate the following specific scoring metrics from 0 to 100 on these dimensions:
- semantic_accuracy_score: 100 perfectly matches intention/meaning, 0 misses meaning entirely.
- entity_preservation_score: 100 keeps all important names/numbers/meds, 0 butchers them.
- hallucination_severity_score: 100 means zero hallucinations, 0 means entirely fabricated.
- translation_fluency_score: 100 means the english reads perfectly natural, 0 means broken grammar.

Provide a detailed accuracy report strictly structured as a valid JSON object matching this schema. Output absolutely nothing else (no markdown blocks, no extra text):
{{
  "audio_metadata": {{
    "primary_language_spoken": "e.g., Korean, English, etc.",
    "number_of_speakers": 2,
    "speaker_genders": "e.g., 1 Male, 1 Female",
    "audio_quality": "e.g., Clear, Noisy, Muffled"
  }},
  "metrics": {{
    "semantic_accuracy_score": 85,
    "entity_preservation_score": 90,
    "hallucination_severity_score": 100,
    "translation_fluency_score": 80
  }},
  "diarization_insights": {{
    "accuracy": "High/Medium/Low",
    "insight": "Clear speaker turns, some overlapping, etc. Detail if the transcript correctly separated voices."
  }},
  "medical_errors": [
    {{"error_type": "dosage", "description": "ASR said 50mg but audio said 15mg."}},
    {{"error_type": "hypo/hyper", "description": "ASR stated hypertension instead of hypotension."}}
  ],
  "named_entities": [
    {{
      "word": "Ibuprofen",
      "type": "Medication",
      "timestamp": "00:00:15",
      "context_sentence": "I take Ibuprofen daily.",
      "status": "correct",
      "correction": null
    }},
    {{
      "word": "hypertension",
      "type": "Diagnosis",
      "timestamp": "00:00:30",
      "context_sentence": "I have hypertension.",
      "status": "incorrect",
      "correction": "hypotension"
    }}
  ],
  "corrected_transcript": [
    {{"speaker": "Speaker 1", "timestamp": "00:00:00-00:00:05", "text": "Corrected english text", "is_changed": true}},
    {{"speaker": "Speaker 2", "timestamp": "00:00:06-00:00:10", "text": "Another line", "is_changed": false}}
  ],
  "assumptions": ["assumption 1", "assumption 2"],
  "missed_information": ["missed point 1", "missed point 2"],
  "incorrect_information": ["incorrect point 1"],
  "risk_rate": "High" | "Medium" | "Low",
  "punctuation_and_grammar_errors": ["error 1"],
  "detailed_analysis": "Comprehensive paragraph explaining overall quality...",
  "final_score": 85
}}
"""
            
            # Configuration to return strict JSON response format
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ]
            )
            
            response = self.client.models.generate_content(
                model='gemini-3.1-pro-preview',
                contents=[uploaded_file, prompt], 
                config=config
            )
            
            result_json = response.text.strip()
            # Clean up markdown if the LLM ignores instructions slightly
            if result_json.startswith("```json"):
                result_json = result_json[7:-3].strip()
            elif result_json.startswith("```"):
                result_json = result_json[3:-3].strip()
                
            parsed = json.loads(result_json)
            
            return parsed
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            if uploaded_file:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except:
                    pass

    def translate_snippet(self, audio_file_path, start_time, end_time, language="English"):
        if self.model_provider == "gemini":
            uploaded_file = None
            try:
                uploaded_file = self.client.files.upload(file=audio_file_path)
                time.sleep(3)
                prompt = f"Translate the speech in this audio exactly from timestamp {start_time} to {end_time} into {language}. Be precise and professional. Output ONLY the translated text and nothing else."
                
                response = self.client.models.generate_content(
                    model='gemini-1.5-pro',
                    contents=[uploaded_file, prompt]
                )
                return {"snippet_translation": response.text.strip()}
            except Exception as e:
                return {"error": str(e)}
            finally:
                if uploaded_file:
                    try:
                        self.client.files.delete(name=uploaded_file.name)
                    except:
                        pass
        return {"error": "Native audio clipping translation not supported for this provider."}

    def chat_with_audio(self, audio_file_path, question):
        if self.model_provider == "gemini":
            uploaded_file = None
            try:
                uploaded_file = self.client.files.upload(file=audio_file_path)
                time.sleep(3)
                prompt = f"Listen closely to the audio file provided. Answer the following question accurately, clearly, and concisely purely based on the audio content. Question: {question}"
                
                response = self.client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=[uploaded_file, prompt]
                )
                return {"chat_response": response.text.strip()}
            except Exception as e:
                return {"error": str(e)}
            finally:
                if uploaded_file:
                    try:
                        self.client.files.delete(name=uploaded_file.name)
                    except:
                        pass
        return {"error": "Native audio chatting not supported for this provider."}
