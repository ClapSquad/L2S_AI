"""
RunPod Serverless Handler for L2S AI Video Processing
This is the main entry point that RunPod calls to process videos
"""

import runpod
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import os
import tempfile
import requests
import time
import yaml

# Configure logging to be more robust
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Silence overly verbose loggers from libraries
logging.getLogger("open_clip").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

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
        self.device = "cuda" if os.getenv("USE_GPU", "1") == "1" else "cpu"
        logger.info(f"Initializing VideoProcessor on device: {self.device}")
        self._load_config()
        
    def load_whisper(self, model_size="medium"):
        """Load Whisper model (cached in network volume)"""
        if self.whisper_model is not None:
            return self.whisper_model
            
        logger.info(f"Loading Whisper {model_size}...")
        from faster_whisper import WhisperModel
        
        # faster-whisper handles caching via the download_root parameter.
        # The library will download the model to the specified directory if it's not already there.
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
        self.whisper_model = WhisperModel(
            model_size,
            device=self.device,
            compute_type=compute_type,
            download_root=str(MODEL_DIR)
        )
        
        logger.info("Whisper loaded!")
        return self.whisper_model
    
    def load_clip(self):
        """Load CLIP model (cached in network volume)"""
        if self.clip_model is not None:
            return self.clip_model
            
        logger.info("Loading CLIP...")
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
        logger.info("CLIP loaded!")
        return self.clip_model, self.clip_preprocess

    def _load_config(self):
        """Load the main config.yaml file"""
        config_path = "src/core/highlight_detection/config.yaml"
        logger.info(f"Loading configuration from {config_path}")
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        logger.info("Configuration loaded.")
    
    def download_video(self, url: str) -> Path:
        """Download video from Supabase URL"""
        logger.info(f"Downloading video from {url}")
        
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
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        logging.info(f"DEBUG: SUPABASE_URL={supabase_url}, SUPABASE_KEY={'set' if supabase_key else 'not set'}  ")
        
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
        
        whisper = self.load_whisper(os.getenv("WHISPER_MODEL_SIZE", "medium"))
        
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
    
    def extract_highlights(self, video_path: Path, transcription: list, options: dict) -> list:
        """Extract video highlights using CLIP and transcription"""
        logger.info("🎬 Extracting highlights...")
        
        from src.core.highlight_detection.shot_detection import detect_shots
        from src.core.highlight_detection.keyframes import extract_keyframes
        from src.core.highlight_detection.feature_scoring import compute_hd_branch
        
        # 1. Detect shots in the video
        shots = detect_shots(str(video_path))
        if not shots:
            logger.warning("No shots detected in the video.")
            return []
        
        # 2. Extract keyframes from each shot
        extract_keyframes(str(video_path), shots)
        
        # 3. Use the loaded config for the HD branch
        # The `compute_hd_branch` function from your project already handles
        # loading the CLIP model, getting text/video features, and scoring.
        scored_shots = compute_hd_branch(
            video_path=str(video_path),
            shots=shots,
            title="", # Title and summary are not used in the handler context
            summary="",
            cfg=self.config['hd_branch']
        )
        
        # 4. Select the top N shots as highlights
        highlights_count = options.get('highlights_count', 5)
        scored_shots.sort(key=lambda x: x.get("HD", 0), reverse=True)
        
        highlights = scored_shots[:highlights_count]
        
        logger.info(f"✅ Found {len(highlights)} highlights")
        return highlights

    def create_summary_video(self, video_path: Path, highlights: list, output_path: Path):
        """Create summary video from highlights"""
        logger.info("✂️  Creating summary video...")

        if not highlights:
            logger.warning("No highlights provided to create a summary video.")
            return None

        # Import the robust video cutting function from your project
        from src.core.video_processing.video_processor import cut_video_by_timestamps

        # Prepare timestamps in the format required by cut_video_by_timestamps: [(start, end), ...]
        timestamps = [(h["start"], h["end"]) for h in highlights]

        # Use the existing function to cut and concatenate the video
        cut_video_by_timestamps(
            video_path=str(video_path), timestamps=timestamps, output_path=str(output_path)
        )

        logger.info(f"✅ Summary created: {output_path}")
        return output_path


# Global processor instance (reused across warm starts)
processor = VideoProcessor()


def process_video(job):
    """
    Main processing function called by RunPod.
    Argument is the entire job object: {"id": "...", "input": {...}}
    """
    # 1. Initialize variables at the very top so the 'except' block can access them
    job_input = job.get("input", {})
    webhook_url = None
    job_id = None

    try:
        # 2. Safely extract job_id and webhook_url first
        job_id = job_input.get('job_id', job.get('id')) # Fallback to RunPod ID if not in input
        webhook_url = job_input.get('webhook_url')

        logger.info("=" * 50)
        logger.info(f"Starting video processing for Job ID: {job_id}")
        
        # 3. Check for required video_url AFTER extracting the basics
        video_url = job_input.get('video_url')
        if not video_url:
            raise ValueError("Missing 'video_url' in input payload")

        options = job_input.get('options', {})
        
        # --- Processing Steps ---
        
        # Step 1: Download
        video_path = processor.download_video(video_url)
        
        # Step 2: Transcribe
        transcription = processor.transcribe_video(
            video_path,
            language=options.get('language', 'auto')
        )
        
        # Step 3: Extract highlights (Dummy implementation for now)
        highlights = processor.extract_highlights(video_path, transcription, options)
        
        # Step 4: Create summary (Dummy implementation for now)
        output_path = Path(tempfile.mktemp(suffix=".mp4"))
        processor.create_summary_video(video_path, highlights, output_path)
        
        # Step 5: Upload results
        result_url = processor.upload_to_supabase(
            output_path,
            bucket="outputs",
            destination=f"{job_id}/summary.mp4"
        )
        
        # Step 6: Send success webhook
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
        if video_path.exists(): video_path.unlink()
        if output_path.exists(): output_path.unlink()
        
        logger.info("✅ Processing complete!")
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": result_url,
            "transcription": transcription[:5], 
            "highlights_count": len(highlights)
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing job {job_id}: {e}", exc_info=True)
        
        # Send error webhook (Only if we successfully parsed the URL)
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                })
            except Exception as webhook_err:
                logger.error(f"Failed to send error webhook: {webhook_err}")
        
        # Return error to RunPod
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