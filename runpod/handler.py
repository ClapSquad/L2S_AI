"""
RunPod Serverless Handler for L2S AI Video Processing
======================================================
This handler orchestrates the complete video processing pipeline including:
- Video download and transcription
- Highlight extraction (LLM or EchoFusion method)
- Summary video creation
- Karaoke-style subtitles (optional) - Burns animated captions into the video
- Vertical cropping (optional) - Converts to 9:16 format for Shorts/Reels
- Upload to Supabase storage

Supported Tasks:
- "process_video": Full video processing pipeline
- "generate_thumbnail": Generate thumbnail from video
"""

import os
import sys
import tempfile
import logging
import requests
import yaml
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

# Configure logging
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

# Try to import RunPod (may not be available in local testing)
try:
    import runpod
except ImportError:
    logger.warning("RunPod not installed. Running in local mode.")
    runpod = None

# Model cache directory (RunPod Network Volume)
MODEL_DIR = Path(os.getenv("MODEL_CACHE_DIR", "/runpod-volume/models"))
MODEL_DIR.mkdir(exist_ok=True, parents=True)

logger.info(f"Model directory: {MODEL_DIR}")
logger.info(f"Starting RunPod Serverless Handler...")


class VideoProcessor:
    """
    Main video processing class that handles all operations.
    
    This class is instantiated once when the server starts ("warm start")
    and reused for all subsequent requests for better performance.
    """
    
    def __init__(self):
        """Initialize the processor and load configuration."""
        self.whisper_model = None
        self.clip_model = None
        self.clip_preprocess = None
        self.device = "cuda" if os.getenv("USE_GPU", "1") == "1" else "cpu"
        self.config = {}
        self._load_config()
        logger.info(f"Initializing VideoProcessor on device: {self.device}")

    def _load_config(self):
        """Load configuration from YAML file"""
        # Try multiple possible config locations
        config_paths = [
            Path(__file__).parent / "config" / "config.yaml",
            Path("src/core/highlight_detection/config.yaml"),
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"Configuration loaded from {config_path}")
                return
        
        logger.warning("No config file found. Using defaults.")
        self.config = {}

    # =========================================================================
    # STEP 1: Download Video
    # =========================================================================
    def download_video(self, url: str) -> Path:
        """
        Download video from a URL (typically Supabase storage).
        
        Args:
            url: The public URL of the video to download
            
        Returns:
            Path: Location of the downloaded video file
            
        Example:
            video_path = processor.download_video("https://supabase.../video.mp4")
        """
        logger.info(f"⬇️  Downloading video from {url[:50]}...")
        
        temp_file = Path(tempfile.mktemp(suffix=".mp4"))
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✅ Downloaded to {temp_file}")
        return temp_file

    # =========================================================================
    # STEP 2: Transcribe Video
    # =========================================================================
    def transcribe_video(self, video_path: Path, language: str = "auto", model_size: str = "small") -> list:
        """
        Convert video audio to text using Whisper AI.
        
        This produces segment-level transcription (sentences/phrases with timestamps).
        
        Args:
            video_path: Path to the video file
            language: Language code ('ko', 'en', 'auto' for automatic detection)
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            
        Returns:
            list: [{"start": 0.0, "end": 2.5, "text": "Hello world"}, ...]
        """
        logger.info(f"🎤 Transcribing {video_path} using '{model_size}' model...")
        
        from src.core.video_processing.video_to_audio import convert_video_to_audio
        from src.core.audio_processing.audio_to_text import transcribe_audio
        
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Step 1: Extract audio from video
            audio_file_name = convert_video_to_audio(str(video_path), str(temp_dir))
            if not audio_file_name:
                raise RuntimeError("Audio conversion failed")
            
            audio_path = temp_dir / audio_file_name

            # Step 2: Transcribe audio to text
            transcribed_segments = transcribe_audio(str(audio_path), model_name=model_size)
            if not isinstance(transcribed_segments, list):
                raise RuntimeError(f"Transcription failed: {transcribed_segments}")

            # Step 3: Format output
            # Input: [(text, (start_time, end_time)), ...]
            # Output: [{"start": start, "end": end, "text": text}, ...]
            transcription = [
                {"start": start, "end": end, "text": text}
                for text, (start, end) in transcribed_segments
            ]

            logger.info(f"✅ Transcribed {len(transcription)} segments")
            return transcription
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def transcribe_for_subtitles(self, video_path: Path, model_size: str = "base") -> list:
        """
        Transcribe video with WORD-LEVEL timestamps for karaoke subtitles.
        
        This is different from regular transcription - we need individual word timings
        so each word can be highlighted as it's spoken.
        
        Args:
            video_path: Path to the video file
            model_size: Whisper model size
            
        Returns:
            list: [{"word": "Hello", "start": 0.0, "end": 0.3}, ...]
        """
        logger.info(f"🎤 Transcribing for karaoke subtitles: {video_path}")
        
        from src.core.video_processing.video_to_audio import convert_video_to_audio
        from src.core.audio_processing.audio_to_text_enhanced import transcribe_for_karaoke
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Convert video to audio
            audio_file_name = convert_video_to_audio(str(video_path), str(temp_dir))
            if not audio_file_name:
                raise RuntimeError("Audio conversion failed")
            
            audio_path = temp_dir / audio_file_name
            
            # Transcribe with word-level timestamps
            words = transcribe_for_karaoke(str(audio_path), model_size)
            
            if isinstance(words, str):  # Error message returned
                raise RuntimeError(f"Transcription failed: {words}")
            
            if not words:
                raise RuntimeError("No words detected in audio")
            
            logger.info(f"✅ Detected {len(words)} words for subtitles")
            return words
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    # =========================================================================
    # STEP 3: Get Summarization (Title + Summary + Timestamps)
    # =========================================================================
    def get_summarization_from_video(self, video_path: Path):
        """
        Use LLM (Gemini) to analyze the video and generate:
        1. A catchy "hook title" for the short video
        2. A summary of the content
        3. Timestamps of the most important moments
        
        Returns:
            tuple: (hook_title, summarized_segments, llm_timestamps)
        """
        logger.info("🧠 Running LLM summarization...")
        
        from src.core.summarization.video_to_summarization import video_to_summarization
        
        try:
            hook_title, summarized_segments, llm_timestamps = video_to_summarization(video_path)
            logger.info(f"✅ Summarization complete. Title: '{hook_title}'")
            return hook_title, summarized_segments, llm_timestamps
        except Exception as e:
            logger.error(f"Error in summarization pipeline: {e}", exc_info=True)
            return None, None, []

    # =========================================================================
    # STEP 4: Extract Highlights
    # =========================================================================
    def extract_highlights_echofusion(self, video_path: Path, llm_timestamps: list, 
                                       summarized_segments: str, options: dict) -> list:
        """
        Use EchoFusion pipeline to detect highlights by combining:
        - Visual features (motion, scene changes)
        - Audio features (volume, speech patterns)  
        - Text features (what's being said)
        
        Returns:
            list: [{"start": 0.0, "end": 10.0, "score": 0.95}, ...]
        """
        logger.info("🎬 Extracting highlights with EchoFusion...")
        
        from src.core.highlight_detection.highlight_pipeline import run_echofusion

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

        highlights = [
            {"start": start, "end": end, "score": score} 
            for start, end, score, rank in predictions
        ]
        
        logger.info(f"✅ Found {len(highlights)} highlights via EchoFusion")
        return highlights

    # =========================================================================
    # STEP 5: Create Summary Video
    # =========================================================================
    def create_summary_video(self, video_path: Path, highlights: list, output_path: Path):
        """
        Cut highlight segments from the original video and concatenate them.
        
        Think of it like making a "best moments" compilation.
        """
        logger.info("✂️  Creating summary video...")

        if not highlights:
            logger.warning("No highlights provided. Cannot create summary video.")
            return None

        from src.core.video_processing.video_processor import cut_video_by_timestamps

        timestamps = [(h["start"], h["end"]) for h in highlights]

        cut_video_by_timestamps(
            video_path=str(video_path), 
            timestamps=timestamps, 
            output_path=str(output_path)
        )

        logger.info(f"✅ Summary video created: {output_path}")
        return output_path

    # =========================================================================
    # STEP 6: Convert to Vertical Format
    # =========================================================================
    def convert_to_vertical(self, video_path: Path, output_path: Path, 
                            crop_method: str = "center") -> Path:
        """
        Convert a horizontal (16:9) video to vertical (9:16) for Shorts/Reels/TikTok.
        
        Args:
            video_path: Input video (usually 16:9 horizontal)
            output_path: Where to save the vertical video
            crop_method: 
                - "center": Crops the center portion (loses sides)
                - "blur": Keeps full video in center with blurred background
            
        Returns:
            Path: Path to the vertical video
        """
        logger.info(f"📱 Converting to vertical (9:16) using '{crop_method}' method...")
        
        from src.core.video_processing.video_exporter import export_social_media_vertical_video
        
        export_social_media_vertical_video(
            input_path=str(video_path),
            output_path=str(output_path),
            resolution="1080x1920",
            bitrate="15M",
            crop_method=crop_method
        )
        
        logger.info(f"✅ Vertical video created: {output_path}")
        return output_path

    # =========================================================================
    # STEP 7: Add Karaoke Subtitles
    # =========================================================================
    def burn_karaoke_subtitles(
        self,
        video_path: Path,
        output_path: Path,
        words: list,
        style: str = "dynamic",
        video_width: int = 1080,
        video_height: int = 1920,
        words_per_line: int = 3
    ) -> Path:
        """
        Burn karaoke-style subtitles into the video.
        
        Creates TikTok/Reels style captions where each word is highlighted
        as it's spoken.
        
        Args:
            video_path: Input video
            output_path: Where to save the subtitled video
            words: Word timing data [{"word": "Hello", "start": 0.0, "end": 0.4}, ...]
            style: 
                - "dynamic": Neon green highlight, centered on screen (TikTok style)
                - "casual": Yellow highlight, bottom of screen with shadow
            video_width: Video width in pixels
            video_height: Video height in pixels
            words_per_line: How many words to show at once (3-4 recommended)
            
        Returns:
            Path: Path to the output video with burned subtitles
        """
        logger.info(f"🔥 Burning {style} karaoke subtitles...")
        
        from src.core.subtitles.subtitle_burner import burn_karaoke_subtitles
        
        # Validate style - only allow "dynamic" or "casual"
        if style not in ["dynamic", "casual"]:
            logger.warning(f"Unknown style '{style}', defaulting to 'dynamic'")
            style = "dynamic"
        
        result = burn_karaoke_subtitles(
            video_path=str(video_path),
            words=words,
            output_path=str(output_path),
            style=style,
            video_width=video_width,
            video_height=video_height,
            words_per_line=words_per_line,
            karaoke_mode="word_by_word"  # Best for short-form content
        )
        
        logger.info(f"✅ Subtitles burned: {result}")
        return Path(result)



    # =========================================================================
    # STEP 8: Upload to Supabase Storage
    # =========================================================================
    def upload_to_supabase(self, file_path: Path, bucket: str, destination: str) -> str:
        """
        Upload a file to Supabase Storage and get its public URL.
        
        Args:
            file_path: Local file to upload
            bucket: Supabase storage bucket name ("outputs", "thumbnails", etc.)
            destination: Path within the bucket ("job123/summary.mp4")
            
        Returns:
            str: Public URL of the uploaded file
        """
        import mimetypes
        from supabase import create_client
        
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        logger.info(f"⬆️  Uploading to Supabase: {bucket}/{destination}")
        
        supabase = create_client(supabase_url, supabase_key)

        with open(file_path, 'rb') as f:
            response = supabase.storage.from_(bucket).upload(
                destination,
                f,
                file_options={"content-type": mime_type}
            )
        
        public_url = supabase.storage.from_(bucket).get_public_url(destination)
        
        logger.info(f"✅ Uploaded: {public_url}")
        return public_url

    # =========================================================================
    # UTILITY: Generate Thumbnail
    # =========================================================================
    def generate_thumbnail(self, video_path: str, output_path: str, 
                           timestamp: str = "00:00:01", 
                           width: int = 640, height: int = -1, quality: int = 2) -> bool:
        """
        Extract a single frame from a video to use as a thumbnail.
        
        Args:
            video_path: Input video
            output_path: Where to save the thumbnail (.jpg)
            timestamp: Time to extract frame from (HH:MM:SS)
            width: Thumbnail width (height auto-calculated if -1)
            quality: JPEG quality (1-31, lower = better)
            
        Returns:
            bool: True if successful
        """
        import subprocess
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False

        try:
            command = [
                "ffmpeg",
                "-ss", timestamp,
                "-an", "-dn", "-sn",
                "-i", video_path,
                "-vframes", "1",
                "-vf", f"scale={width}:{height}",
                "-q:v", str(quality),
                "-y",
                output_path
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
            else:
                logger.error("Thumbnail file was not created")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return False


# =============================================================================
# GLOBAL PROCESSOR INSTANCE (reused across warm starts)
# =============================================================================
processor = VideoProcessor()


# =============================================================================
# MAIN VIDEO PROCESSING FUNCTION
# =============================================================================
def process_video(job):
    """
    Main video processing function called by RunPod.
    
    Expected input payload:
    {
        "input": {
            "job_id": "abc123",
            "video_url": "https://supabase.../video.mp4",
            "webhook_url": "https://your-backend.com/webhook",
            "options": {
                "method": "echofusion" | "llm_only",
                "language": "auto" | "ko" | "en",
                
                // Subtitle options
                "subtitles": true | false,
                "subtitle_style": "dynamic" | "casual",
                
                // Vertical conversion options  
                "vertical": true | false,
                "crop_method": "center" | "blur",
                
                // EchoFusion options
                "title": "Video title",
                "w_hd": 0.55,
                "w_txt": 0.45,
                "keep_seconds": 60.0
            }
        }
    }
    """
    job_input = job.get("input", {})
    webhook_url = None
    job_id = None
    temp_files = []  # Track temp files for cleanup

    try:
        # ---------------------------------------------------------------------
        # SETUP: Extract job information
        # ---------------------------------------------------------------------
        job_id = job_input.get('job_id', job.get('id'))
        webhook_url = job_input.get('webhook_url')
        video_url = job_input.get('video_url')
        
        if not video_url:
            raise ValueError("Missing 'video_url' in input payload")

        options = job_input.get('options', {})
        whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        
        logger.info("=" * 60)
        logger.info(f"🚀 Starting video processing for Job ID: {job_id}")
        logger.info(f"   Options: {options}")
        logger.info("=" * 60)

        # ---------------------------------------------------------------------
        # STEP 1: Download the video
        # ---------------------------------------------------------------------
        video_path = processor.download_video(video_url)
        temp_files.append(video_path)
        
        # ---------------------------------------------------------------------
        # STEP 2: Transcribe the video
        # ---------------------------------------------------------------------
        transcription = processor.transcribe_video(
            video_path,
            language=options.get('language', 'auto'),
            model_size=whisper_model_size
        )
        
        # ---------------------------------------------------------------------
        # STEP 3: Get LLM summarization
        # ---------------------------------------------------------------------
        hook_title, summarized_segments, llm_timestamps = processor.get_summarization_from_video(video_path)
        
        if not llm_timestamps:
            raise RuntimeError("Failed to generate timestamps from LLM summarization.")
        
        # ---------------------------------------------------------------------
        # STEP 4: Extract highlights
        # ---------------------------------------------------------------------
        method = options.get('method', 'echofusion')
        logger.info(f"Using highlight extraction method: {method}")

        if method == 'llm_only':
            logger.info("💬 Using timestamps directly from LLM...")
            highlights = [{"start": start, "end": end} for start, end in llm_timestamps]
        else:
            highlights = processor.extract_highlights_echofusion(
                video_path, llm_timestamps, summarized_segments, options
            )

        # ---------------------------------------------------------------------
        # STEP 5: Create summary video
        # ---------------------------------------------------------------------
        summary_video_path = Path(tempfile.mkstemp(suffix=".mp4")[1])
        temp_files.append(summary_video_path)
        processor.create_summary_video(video_path, highlights, summary_video_path)
        
        current_video_path = summary_video_path

        # ---------------------------------------------------------------------
        # STEP 6: Convert to vertical if enabled
        # ---------------------------------------------------------------------
        vertical_applied = False
        if options.get('vertical', False):
            logger.info("📱 Vertical option enabled - converting to 9:16...")
            
            vertical_path = Path(tempfile.mkstemp(suffix="_vertical.mp4")[1])
            temp_files.append(vertical_path)
            
            crop_method = options.get('crop_method', 'center')
            processor.convert_to_vertical(
                video_path=current_video_path,
                output_path=vertical_path,
                crop_method=crop_method
            )
            
            current_video_path = vertical_path
            vertical_applied = True
        else:
            logger.info("📱 Vertical conversion: disabled")

        # ---------------------------------------------------------------------
        # STEP 7: Add karaoke subtitles if enabled
        # ---------------------------------------------------------------------
        subtitles_applied = False
        if options.get('subtitles', False):
            logger.info("📝 Subtitles enabled - starting karaoke subtitle pipeline...")
            
            subtitle_style = options.get('subtitle_style', 'dynamic')
            if subtitle_style not in ['dynamic', 'casual']:
                logger.warning(f"Invalid subtitle_style '{subtitle_style}', using 'dynamic'")
                subtitle_style = 'dynamic'
            
            try:
                # Transcribe for word-level timestamps
                words = processor.transcribe_for_subtitles(
                    current_video_path,
                    model_size=whisper_model_size
                )
                
                # Burn subtitles
                subtitled_path = Path(tempfile.mkstemp(suffix="_subtitled.mp4")[1])
                temp_files.append(subtitled_path)
                
                processor.burn_karaoke_subtitles(
                    video_path=current_video_path,
                    output_path=subtitled_path,
                    words=words,
                    style=subtitle_style,
                    video_width=options.get('video_width', 1080),
                    video_height=options.get('video_height', 1920),
                    words_per_line=options.get('words_per_line', 3)
                )
                
                current_video_path = subtitled_path
                subtitles_applied = True
                logger.info(f"✅ Karaoke subtitles burned with style: {subtitle_style}")
                
            except Exception as sub_error:
                logger.error(f"⚠️ Subtitle burning failed: {sub_error}", exc_info=True)
                logger.info("Continuing with video without subtitles...")
        else:
            logger.info("📝 Subtitles: disabled")

        # ---------------------------------------------------------------------
        # STEP 8: Upload to Supabase
        # ---------------------------------------------------------------------
        result_url = processor.upload_to_supabase(
            current_video_path,
            bucket="outputs",
            destination=f"{job_id}/summary.mp4"
        )
        
        # ---------------------------------------------------------------------
        # STEP 9: Send success webhook
        # ---------------------------------------------------------------------
        if webhook_url:
            logger.info(f"📤 Sending success webhook to {webhook_url}")
            requests.post(webhook_url, json={
                "job_id": job_id,
                "status": "completed",
                "result_url": result_url,
                "transcription": transcription,
                "highlights": highlights,
                "hook_title": hook_title,
                "options_applied": {
                    "method": method,
                    "subtitles": subtitles_applied,
                    "subtitle_style": options.get('subtitle_style', 'dynamic') if subtitles_applied else None,
                    "vertical": vertical_applied,
                    "crop_method": options.get('crop_method', 'center') if vertical_applied else None
                }
            })
        
        # ---------------------------------------------------------------------
        # CLEANUP
        # ---------------------------------------------------------------------
        for temp_file in temp_files:
            try:
                if isinstance(temp_file, Path) and temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")
        
        logger.info("=" * 60)
        logger.info("✅ Processing complete!")
        logger.info("=" * 60)
        
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": result_url,
            "transcription": transcription[:5],  # First 5 segments as preview
            "highlights_count": len(highlights),
            "hook_title": hook_title,
            "options_applied": {
                "method": method,
                "subtitles": subtitles_applied,
                "vertical": vertical_applied
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing job {job_id}: {e}", exc_info=True)
        
        # Send error webhook
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                })
            except Exception as webhook_err:
                logger.error(f"Failed to send error webhook: {webhook_err}")
        
        # Cleanup on error
        for temp_file in temp_files:
            try:
                if isinstance(temp_file, Path) and temp_file.exists():
                    temp_file.unlink()
            except:
                pass
        
        return {
            "status": "error",
            "job_id": job_id,
            "error": str(e)
        }


# =============================================================================
# THUMBNAIL PROCESSING FUNCTION
# =============================================================================
def process_thumbnail(job):
    """
    Generate a thumbnail from a video.
    
    Input:
    {
        "input": {
            "job_id": "abc123",
            "video_url": "https://supabase.../video.mp4",
            "webhook_url": "https://your-backend.com/webhook"
        }
    }
    """
    job_input = job.get("input", {})
    webhook_url = None
    job_id = None

    try:
        job_id = job_input.get('job_id', job.get('id'))
        webhook_url = job_input.get('webhook_url')

        logger.info("=" * 50)
        logger.info(f"📸 Starting thumbnail generation for Job ID: {job_id}")

        video_url = job_input.get('video_url')
        if not video_url:
            raise ValueError("Missing 'video_url' in input payload")

        # Download video
        video_path = processor.download_video(video_url)

        # Generate thumbnail
        output_path = Path(tempfile.mkstemp(suffix=".jpg")[1])
        processor.generate_thumbnail(str(video_path), str(output_path))

        # Upload to Supabase
        result_url = processor.upload_to_supabase(
            output_path,
            bucket="thumbnails",
            destination=f"{job_id}.jpg"
        )

        # Send webhook
        if webhook_url:
            logger.info(f"Sending webhook to {webhook_url}")
            requests.post(webhook_url, json={
                "job_id": job_id,
                "status": "completed",
                "result_url": result_url
            })

        # Cleanup
        if video_path.exists():
            video_path.unlink()
        if output_path.exists():
            output_path.unlink()

        logger.info("✅ Thumbnail generation complete!")
        
        return {
            "status": "success",
            "job_id": job_id,
            "result_url": result_url
        }

    except Exception as e:
        logger.error(f"❌ Error generating thumbnail for job {job_id}: {e}", exc_info=True)

        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(e)
                })
            except Exception as webhook_err:
                logger.error(f"Failed to send error webhook: {webhook_err}")

        return {
            "status": "error",
            "job_id": job_id,
            "error": str(e)
        }


# =============================================================================
# TASK ROUTER
# =============================================================================
def handler(job):
    """
    Main entry point for RunPod.
    
    Routes jobs to the appropriate processor based on the 'task' field.
    
    Supported tasks:
    - "process_video": Full video processing pipeline
    - "generate_thumbnail": Generate thumbnail from video
    
    Example input:
    {
        "input": {
            "task": "process_video",
            "job_id": "abc123",
            "video_url": "https://...",
            ...
        }
    }
    """
    job_input = job.get("input", {})
    task = job_input.get("task", "process_video")
    
    logger.info(f"📋 Received task: {task}")
    
    if task == "process_video":
        return process_video(job)
    elif task == "generate_thumbnail":
        return process_thumbnail(job)
    else:
        return {
            "status": "error",
            "error": f"Unknown task: {task}. Supported: process_video, generate_thumbnail"
        }


# =============================================================================
# START THE RUNPOD SERVER
# =============================================================================
if __name__ == "__main__":
    if runpod:
        logger.info("🚀 Starting RunPod serverless handler...")
        logger.info(f"Model cache directory: {MODEL_DIR}")
        runpod.serverless.start({"handler": handler})
    else:
        logger.info("Running in local test mode (RunPod not available)")