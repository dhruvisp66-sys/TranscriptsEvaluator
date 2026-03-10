import os
import json
import tempfile
import atexit
import shutil
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from engine import ASREvaluatorEngine

app = FastAPI(title="Meta-Judge ASR Evaluation Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
tmp_dir = tempfile.mkdtemp(prefix="asr_eval2_")
print(f"Created temp dir for audio uploads: {tmp_dir}")

def cleanup_tmp():
    shutil.rmtree(tmp_dir, ignore_errors=True)

atexit.register(cleanup_tmp)

@app.post("/api/evaluate")
async def evaluate_transcript(
    audioFile: UploadFile = File(...),
    transcriptFile: UploadFile = File(...)
):
    try:
        # Save temp audio file
        ext = os.path.splitext(audioFile.filename)[1] or ".wav"
        temp_audio_path = os.path.join(tmp_dir, f"temp_upload{ext}")
        with open(temp_audio_path, "wb") as f:
            f.write(await audioFile.read())
            
        # Parse transcript
        raw_transcript_content = (await transcriptFile.read()).decode('utf-8')
        transcript_content = raw_transcript_content
        try:
            transcript_json = json.loads(raw_transcript_content)
            if "text" in transcript_json:
                transcript_content = transcript_json["text"]
            elif "results" in transcript_json and "channels" in transcript_json["results"]:
                transcript_content = transcript_json["results"]["channels"][0]["alternatives"][0]["transcript"]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        
        # Dual-judge evaluation
        engine = ASREvaluatorEngine()
        result = await engine.evaluate_both(temp_audio_path, transcript_content)
        
        try:
            os.unlink(temp_audio_path)
        except:
            pass
            
        return result
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def read_root():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
