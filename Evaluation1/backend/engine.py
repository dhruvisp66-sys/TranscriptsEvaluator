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
You are an expert ASR (Automatic Speech Recognition) and Translation evaluation judge.
You are provided with an original audio file (which may be in any language) and the generated English transcript for this audio.

Target Transcript to Evaluate:
\"\"\"
{transcript_text}
\"\"\"

Your task is to act as a judge and evaluate the accuracy of the generated English transcript against the original audio.
Since the audio might be in a different language, you must implicitly understand the audio, translate its semantic meaning to English, and evaluate if the generated transcript captures it accurately. Pay extra attention to nuance, context, missed elements and hallucinations.

Provide a detailed accuracy report strictly structured as a valid JSON object matching this schema. Output absolutely nothing else (no markdown blocks, no extra text):
{{
  "assumptions": ["assumption 1", "assumption 2"],
  "missed_information": ["missed point 1", "missed point 2"],
  "incorrect_information": ["incorrect point 1"],
  "risk_rate": "High" | "Medium" | "Low",
  "punctuation_and_grammar_errors": ["error 1"],
  "detailed_analysis": "Comprehensive paragraph explaining overall quality, grammatical corrections, and reasoning...",
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
