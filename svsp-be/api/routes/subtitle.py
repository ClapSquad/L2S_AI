# svsp-be/api/routes/subtitle.py
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
import os, uuid, subprocess, sys

# --- Path setup to import AI utils ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../svsp-ai")))
from utils.audio_to_text import transcribe_audio
from utils.subtitles import segments_to_srt

# --- Router setup ---
router = APIRouter()

# --- Directories ---
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "generated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================================================
# 1️⃣  Upload Route
# ================================================================
@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload a video or audio file to the server"""
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    return {"message": "File uploaded successfully", "file_name": file.filename}


# ================================================================
# 2️⃣  Subtitle (.srt) Generation
# ================================================================
@router.post("/generate-srt/")
async def generate_srt(file_name: str, model_name: str = "base"):
    """Generate only .srt file from uploaded video/audio"""
    input_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="File not found")

    segments = transcribe_audio(input_path, model_name=model_name)

    srt_filename = f"{os.path.splitext(file_name)[0]}_{uuid.uuid4().hex[:6]}.srt"
    srt_path = os.path.join(OUTPUT_DIR, srt_filename)
    segments_to_srt(segments, srt_path)

    return FileResponse(srt_path, media_type="text/plain", filename=srt_filename)


# ================================================================
# 3️⃣  Subtitle Burn/Overlay
# ================================================================
@router.post("/burn-subtitles/")
async def burn_subtitles(file_name: str, burn_in: bool = True):
    """Burn or embed subtitles into the video"""
    input_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Step 1: Transcribe -> SRT
    segments = transcribe_audio(input_path)
    srt_filename = f"{os.path.splitext(file_name)[0]}_{uuid.uuid4().hex[:6]}.srt"
    srt_path = os.path.join(OUTPUT_DIR, srt_filename)
    segments_to_srt(segments, srt_path)

    # Step 2: Add subtitles to video
    out_video = os.path.join(OUTPUT_DIR, f"{os.path.splitext(file_name)[0]}_subtitled.mp4")

    if burn_in:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"subtitles={srt_path}", "-c:a", "copy", out_video]
    else:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-i", srt_path, "-c", "copy", "-c:s", "mov_text", out_video]

    subprocess.run(cmd, check=True)
    return FileResponse(out_video, media_type="video/mp4", filename=os.path.basename(out_video))
