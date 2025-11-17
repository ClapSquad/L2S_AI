from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import sys
import os
import json

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
src_path = os.path.join(project_root, 'src')
assets_path = os.path.join(project_root, 'assets')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

class VideoProcessRequest(BaseModel):
    file_path: str
    method: str = "llm"
    vertical_export: bool = False
    subtitles: bool = False
    title: str = ""

app = FastAPI(
    title="L2S_AI API",
    description="API for the L2S_AI project.",
    version="1.0",
)

@app.get("/", tags=["General"])
def read_root():
    """
    A simple health check endpoint to confirm the server is running.
    """
    return {"status": "ok"}

@app.post("/process-video", tags=["Video Processing"])
def process_video(request: VideoProcessRequest):
    """
    Endpoint to run the video summarization and processing logic.
    It triggers the same logic as `src/main.py` but via an API call.
    """
    command = [
        sys.executable,
        os.path.join(src_path, "main.py"),
        "-f", request.file_path,
        "--method", request.method,
    ]
    if request.vertical_export:
        command.append("--vertical_export")
    if request.subtitles:
        command.append("--subtitles")
    if request.title:
        command.extend(["--title", request.title])

    try:
        # Using subprocess to run the script as it has its own argument parsing and logging
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # The script now prints progress to stderr and the final JSON to stdout.
        # We need to find the JSON output from stdout.
        try:
            # The JSON output might be at the end of other print statements
            json_output_str = process.stdout[process.stdout.rfind('{'):]
            result_data = json.loads(json_output_str)
            download_url = result_data.get("download_url")
            if not download_url:
                raise HTTPException(status_code=500, detail="Processing succeeded, but the script did not return a download URL.")
            
            return {"status": "success", "download_url": download_url, "details": process.stderr}
        except (json.JSONDecodeError, IndexError):
            return {"status": "error", "error": "Failed to parse script output.", "raw_output": process.stdout}

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail={"message": "Video processing script failed.", "stderr": e.stderr})
