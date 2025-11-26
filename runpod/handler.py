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
    
    def transcribe_video(self, video_path: Path, language: str = "auto", model_size: str = "base") -> list:
        """
        Extracts audio from a video, transcribes it using Whisper, and returns
        the transcription with timestamps.
        """
        logger.info(f"🎤 Transcribing {video_path} using '{model_size}' model...")
        from src.core.video_processing.video_to_audio import convert_video_to_audio
        from src.core.audio_processing.audio_to_text import transcribe_audio
        
        temp_dir = Path(tempfile.mkdtemp())
        audio_file_name = None

        try:
            # 1. Convert video to audio 
            audio_file_name = convert_video_to_audio(str(video_path), str(temp_dir))
            if not audio_file_name:
                raise RuntimeError("Audio conversion failed, convert_video_to_audio returned None.")
            
            audio_path = temp_dir / audio_file_name

            # 2. Transcribe the audio file 
            transcribed_segments = transcribe_audio(str(audio_path), model_name=model_size)
            if not isinstance(transcribed_segments, list):
                raise RuntimeError(f"Transcription failed: {transcribed_segments}")

            # 3. Format the output to match the handler's expected format
            transcription = [
                {"start": start, "end": end, "text": text}
                for text, (start, end) in transcribed_segments
            ]

            logger.info(f"✅ Transcribed {len(transcription)} segments")
            return transcription
        finally:
            # 4. Clean up the temporary directory and its contents
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

    def extract_highlights_echofusion(self, video_path: Path, llm_timestamps: list, summarized_segments: str, options: dict) -> list:
        """Extract video highlights using the full EchoFusion pipeline."""
        logger.info("🎬 Extracting highlights with EchoFusion...")
        from src.core.highlight_detection.highlight_pipeline import run_echofusion

        # Extract relevant options for echofusion, with defaults from config
        fusion_cfg = self.config.get("fusion", {})
        w_hd = options.get("w_hd", fusion_cfg.get("w_hd", 0.55))
        w_txt = options.get("w_txt", fusion_cfg.get("w_txt", 0.45))
        w_aud = options.get("w_aud", fusion_cfg.get("w_aud", 0.0))
        keep_seconds = options.get("keep_seconds", fusion_cfg.get("keep_seconds", 60.0))

        predictions = run_echofusion(
            video_path=video_path,
            title=options.get("title", ""),
            summary=summarized_segments,
            llm_timestamps=llm_timestamps,
            w_hd=w_hd,
            w_txt=w_txt,
            w_aud=w_aud,
            keep_seconds=keep_seconds
        )

        # The handler expects a list of dicts with 'start' and 'end' keys
        highlights = [{"start": start, "end": end, "score": score} for start, end, score, rank in predictions]
        logger.info(f"✅ Found {len(highlights)} highlights via EchoFusion")
        return highlights

    def get_summarization_from_video(self, video_path: Path):
        """Runs the initial summarization to get title, summary, and timestamps."""
        logger.info("Initial summarization to get title, summary, and timestamps...")
        from src.core.summarization.video_to_summarization import video_to_summarization
        try:
            hook_title, summarized_segments, llm_timestamps = video_to_summarization(video_path)
            logger.info("✅ Initial summarization complete.")
            return hook_title, summarized_segments, llm_timestamps
        except Exception as e:
            logger.error(f"Error in summarization pipeline: {e}", exc_info=True)
            return None, None, []

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

        # Cut and concatenate the video
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
        whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        transcription = processor.transcribe_video(
            video_path,
            language=options.get('language', 'auto'),
            model_size=whisper_model_size
        )
        
        # Step 3: Get initial summarization and LLM timestamps
        hook_title, summarized_segments, llm_timestamps = processor.get_summarization_from_video(video_path)
        if not llm_timestamps:
            raise RuntimeError("Failed to generate initial timestamps from LLM summarization.")

        # Step 4: Extract highlights based on the selected method
        method = options.get('method', 'echofusion') # Default to echofusion
        logger.info(f"Using highlight extraction method: {method}")

        if method == 'llm_only':
            logger.info("💬 Using timestamps directly from LLM summarization...")
            # Convert list of [start, end] to list of {"start": start, "end": end}
            highlights = [{"start": start, "end": end} for start, end in llm_timestamps]
        else: # Default to 'echofusion' or other future vision-based methods
            highlights = processor.extract_highlights_echofusion(video_path, llm_timestamps, summarized_segments, options)

        # Step 5: Create summary video
        output_path = Path(tempfile.mkstemp(suffix=".mp4")[1])
        processor.create_summary_video(video_path, highlights, output_path)
        
        # Step 6: Upload results
        result_url = processor.upload_to_supabase(
            output_path,
            bucket="outputs",
            destination=f"{job_id}/summary.mp4"
        )
        
        # Step 7: Send success webhook
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