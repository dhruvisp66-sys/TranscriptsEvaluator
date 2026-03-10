import os
import json
import time
import base64
import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import AsyncOpenAI

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class ASREvaluatorEngine:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        # We will use AsyncOpenAI for async capabilities natively
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self.openai_client = AsyncOpenAI(api_key=openai_key)
        else:
            self.openai_client = None

    async def evaluate_both(self, audio_file_path, transcript_text):
        if not self.openai_client:
            return {"error": "OPENAI_API_KEY is not set in the .env file. Please add it to use the dual-judge system."}

        # Run both evaluators concurrently
        gemini_task = asyncio.to_thread(self._evaluate_gemini, audio_file_path, transcript_text)
        openai_task = self._evaluate_openai(audio_file_path, transcript_text)

        results = await asyncio.gather(gemini_task, openai_task, return_exceptions=True)
        
        gemini_result = results[0]
        openai_result = results[1]
        
        # Check for catastrophic errors (e.g. exception thrown instead of returned dict)
        if isinstance(gemini_result, Exception):
            gemini_result = {"error": f"Gemini evaluation failed: {str(gemini_result)}"}
        if isinstance(openai_result, Exception):
            openai_result = {"error": f"OpenAI evaluation failed: {str(openai_result)}"}

        # If both failed, we can't do the meta judge
        if "error" in gemini_result and "error" in openai_result:
            return {
                "gemini": gemini_result,
                "openai": openai_result,
                "meta": {"error": "Both models failed to evaluate the transcript."}
            }

        # Run the meta judge
        meta_result = await self._meta_judge(gemini_result, openai_result, transcript_text)

        return {
            "gemini": gemini_result,
            "openai": openai_result,
            "meta": meta_result
        }

    def _evaluate_gemini(self, audio_file_path, transcript_text):
        uploaded_file = None
        try:
            # Upload the audio file to Gemini File API
            uploaded_file = self.gemini_client.files.upload(file=audio_file_path)
            time.sleep(3) # Wait for processing
            
            prompt = self._get_judge_prompt(transcript_text, "Gemini")
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                ]
            )
            
            response = self.gemini_client.models.generate_content(
                model='gemini-3.1-pro-preview',
                contents=[uploaded_file, prompt], 
                config=config
            )
            return self._parse_json_result(response.text)
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            if uploaded_file:
                try:
                    self.gemini_client.files.delete(name=uploaded_file.name)
                except:
                    pass

    async def _evaluate_openai(self, audio_file_path, transcript_text):
        try:
            # Determine audio format
            ext = os.path.splitext(audio_file_path)[1].lower()
            audio_format = "mp3" if ext == ".mp3" else "wav" # Defaulting to wav for others, though OpenAI supports more
            
            # Read and base64 encode audio
            with open(audio_file_path, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                
            prompt = self._get_judge_prompt(transcript_text, "OpenAI")
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-audio-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert ASR (Automatic Speech Recognition) and Translation evaluation judge. Your output MUST be strict JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_base64,
                                    "format": audio_format
                                }
                            }
                        ]
                    }
                ]
            )
            # We didn't enforce response_format={"type":"json_object"} because audio model sometimes has issues with it globally depending on API updates.
            # But we can parse it from string securely.
            result_text = response.choices[0].message.content
            return self._parse_json_result(result_text)
            
        except Exception as e:
            return {"error": str(e)}

    async def _meta_judge(self, gemini_result, openai_result, transcript_text):
        # We handle this using AsyncOpenAI or AsyncGemini, Let's use OpenAI string completion for the meta, it's fast
        try:
            prompt = f"""
You are the "Meta-Judge". You have been given the evaluation results of two expert AI models (Gemini and OpenAI) regarding an English transcript generated from a non-English audio file.
Your job is to synthesize these results into a cohesive final report.

Transcript Provided:
\"\"\"
{transcript_text}
\"\"\"

Gemini Evaluation JSON:
{json.dumps(gemini_result, indent=2)}

OpenAI Evaluation JSON:
{json.dumps(openai_result, indent=2)}

Synthesize both evaluations to find the ground truth based on their agreements and discrepancies.
Output absolutely nothing else except a valid JSON object matching this exact schema:
{{
  "consensus_score": 85, // An aggregated integer score based on both models
  "agreements": ["What both models agreed was wrong/right"],
  "discrepancies": ["Where Gemini and OpenAI disagreed"],
  "final_verdict": "Comprehensive paragraph summarizing the true quality of the ASR, acknowledging insights from both AI judges."
}}
"""
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a JSON generating system. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            return self._parse_json_result(response.choices[0].message.content)
            
        except Exception as e:
            return {"error": str(e)}

    def _get_judge_prompt(self, transcript_text, judge_name):
        return f"""
You are {judge_name}, an expert ASR and Translation evaluation judge.
You are provided with an original audio file (which may be in any language) and the generated English transcript for this audio.

Target Transcript to Evaluate:
\"\"\"
{transcript_text}
\"\"\"

Act as a judge and evaluate the accuracy of the generated English transcript against the original audio.
Since the audio might be in a different language, translate its semantic meaning to English implicitly and evaluate if the generated transcript captures it accurately. 
Pay extra attention to nuance, context, missed elements and hallucinations.

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

    def _parse_json_result(self, result_json):
        if not result_json:
            return {"error": "Empty response received"}
        result_json = result_json.strip()
        if result_json.startswith("```json"):
            result_json = result_json[7:-3].strip()
        elif result_json.startswith("```"):
            result_json = result_json[3:-3].strip()
            
        try:
            return json.loads(result_json)
        except json.JSONDecodeError:
            return {"error": f"Failed to parse JSON. Raw output: {result_json}"}
