"""
RunPod Serverless Handler for L2S AI Video Processing
This is the main entry point that RunPod calls to process videos
"""

import runpod
import os
import logging
from pathlib import Path
import tempfile
import requests
from typing import Dict, Any
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model cache directory (RunPod Network Volume)
MODEL_DIR = Path(os.getenv("MODEL_CACHE_DIR", "/runpod-volume/models"))
MODEL_DIR.mkdir(exist_ok=True, parents=True)

logger.info(f"Model directory: {MODEL_DIR}")
logger.info(f"Starting RunPod Serverless Handler...")


class VideoProcessor:
    """Main video processing class"""
    
    def __init__(self):
        self.whisper_model = None
        self.clip_model = None
        self.device = "cuda"
        
    def load_whisper(self, model_size="medium"):
        """Load Whisper model (cached in network volume)"""
        if self.whisper_model is not None:
            return self.whisper_model
            
        logger.info(f"Loading Whisper {model_size}...")
        from faster_whisper import WhisperModel
        
        model_path = MODEL_DIR / f"whisper-{model_size}"
        
        if model_path.exists():
            logger.info(f"✅ Using cached model from {model_path}")
        else:
            logger.info(f"⬇️  Downloading model to {model_path}...")
            
        self.whisper_model = WhisperModel(
            model_size,
            device=self.device,
            compute_type="float16",
            download_root=str(MODEL_DIR)
        )
        
        logger.info("Whisper loaded!")
        return self.whisper_model
    
    def load_clip(self):
        """Load CLIP model (cached in network volume)"""
        if self.clip_model is not None:
            return self.clip_model
            
        logger.info("🖼️  Loading CLIP...")
        import open_clip
        import torch
        
        cache_dir = MODEL_DIR / "clip"
        cache_dir.mkdir(exist_ok=True)
        
        self.clip_model, _, self.clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="openai",
            cache_dir=str(cache_dir)
        )
        
        self.clip_model = self.clip_model.cuda()
        logger.info("✅ CLIP loaded!")
        return self.clip_model, self.clip_preprocess
    
    def download_video(self, url: str) -> Path:
        """Download video from Supabase URL"""
        logger.info(f"⬇️  Downloading video from {url}")
        
        # Create temp file
        temp_file = Path(tempfile.mktemp(suffix=".mp4"))
        
        # Download
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✅ Downloaded to {temp_file}")
        return temp_file
    
    def upload_to_supabase(self, file_path: Path, bucket: str, destination: str) -> str:
        """Upload file to Supabase Storage"""
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        logger.info(f"⬆️  Uploading to Supabase: {bucket}/{destination}")
        
        supabase = create_client(supabase_url, supabase_key)
        
        with open(file_path, 'rb') as f:
            response = supabase.storage.from_(bucket).upload(
                destination,
                f,
                file_options={"content-type": "video/mp4"}
            )
        
        # Get public URL
        public_url = supabase.storage.from_(bucket).get_public_url(destination)
        
        logger.info(f"✅ Uploaded: {public_url}")
        return public_url
    
    def transcribe_video(self, video_path: Path, language: str = "auto") -> list:
        """Transcribe audio using Whisper"""
        logger.info(f"🎤 Transcribing {video_path}...")
        
        whisper = self.load_whisper("medium")
        
        segments, info = whisper.transcribe(
            str(video_path),
            language=None if language == "auto" else language,
            beam_size=5
        )
        
        transcription = []
        for segment in segments:
            transcription.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        
        logger.info(f"✅ Transcribed {len(transcription)} segments")
        return transcription
    
    def extract_highlights(self, video_path: Path, transcription: list) -> list:
        """Extract video highlights using CLIP and transcription"""
        logger.info("🎬 Extracting highlights...")
        
        # TODO: Implement your highlight extraction logic
        # This is a placeholder
        
        highlights = [
            {"start": 0, "end": 10, "score": 0.9},
            {"start": 30, "end": 40, "score": 0.85},
        ]
        
        logger.info(f"✅ Found {len(highlights)} highlights")
        return highlights
    
    def create_summary_video(self, video_path: Path, highlights: list, output_path: Path):
        """Create summary video from highlights"""
        logger.info("✂️  Creating summary video...")
        
        import ffmpeg
        
        # TODO: Implement your video editing logic using FFmpeg
        # This is a placeholder
        
        # Example: Concatenate highlight clips
        # ffmpeg.concat(...).output(str(output_path)).run()
        
        logger.info(f"✅ Summary created: {output_path}")
        return output_path


# Global processor instance (reused across warm starts)
processor = VideoProcessor()


def process_video(job_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main processing function called by RunPod
    
    Expected input:
    {
        "video_url": "https://supabase.co/.../video.mp4",
        "job_id": "12345",
        "options": {
            "language": "en",
            "duration": 60,
            "highlights_count": 5
        },
        "webhook_url": "https://your-backend.com/api/runpod-webhook"
    }
    """
    try:
        logger.info("=" * 50)
        logger.info("Starting video processing...")
        logger.info(f"Job ID: {job_input.get('job_id')}")
        
        # Extract inputs
        video_url = job_input['video_url']
        job_id = job_input['job_id']
        options = job_input.get('options', {})
        webhook_url = job_input.get('webhook_url')
        
        # Step 1: Download video from Supabase
        video_path = processor.download_video(video_url)
        
        # Step 2: Transcribe
        transcription = processor.transcribe_video(
            video_path,
            language=options.get('language', 'auto')
        )
        
        # Step 3: Extract highlights
        highlights = processor.extract_highlights(video_path, transcription)
        
        # Step 4: Create summary video
        output_path = Path(tempfile.mktemp(suffix=".mp4"))
        processor.create_summary_video(video_path, highlights, output_path)
        
        # Step 5: Upload results to Supabase
        result_url = processor.upload_to_supabase(
            output_path,
            bucket="outputs",
            destination=f"{job_id}/summary.mp4"
        )
        
        # Step 6: Send webhook to your backend
        if webhook_url:
            logger.info(f"Sending webhook to {webhook_url}")
            requests.post(webhook_url, json={
                "job_id": job_id,
                "status": "completed",
                "result_url": result_url,
                "transcription": transcription,
                "highlights": highlights
            })
        
        # Cleanup
        video_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        
        logger.info("✅ Processing complete!")
        logger.info("=" * 50)
        
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": result_url,
            "transcription": transcription[:5],  # First 5 segments
            "highlights_count": len(highlights)
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing video: {e}", exc_info=True)
        
        # Send error webhook
        if webhook_url:
            requests.post(webhook_url, json={
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            })
        
        return {
            "status": "error",
            "error": str(e)
        }


# RunPod serverless entry point
if __name__ == "__main__":
    logger.info("Starting RunPod Serverless Handler...")
    logger.info(f"Model cache directory: {MODEL_DIR}")
    
    # Start the serverless handler
    runpod.serverless.start({
        "handler": process_video,
        "return_aggregate_stream": True
    })