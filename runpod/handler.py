"""
RunPod Handler for Video Processing
===================================
This handler orchestrates the complete video processing pipeline including:
- Video download and transcription
- Highlight extraction (LLM or EchoFusion method)
- Summary video creation
- Subtitles (optional) - Burns captions into the video
- Vertical cropping (optional) - Converts to 9:16 format for Shorts/Reels
- Upload to Supabase storage
"""

import os
import sys
import tempfile
import logging
import requests
import yaml
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import RunPod (may not be available in local testing)
try:
    import runpod
except ImportError:
    logger.warning("RunPod not installed. Running in local mode.")
    runpod = None


class VideoProcessor:
    """
    Main video processing class that handles all operations.
    """
    
    def __init__(self):
        """
        Initialize the processor.
        This runs once when the server starts (called "warm start").
        """
        self.clip_model = None
        self.clip_preprocess = None
        self.config = {}
        self._load_config()
    
    def _load_clip(self):
        """Lazy-load CLIP model (only when needed for EchoFusion)"""
        if self.clip_model is None:
            import clip
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=device)
            logger.info(f"CLIP model loaded on {device}")
        return self.clip_model, self.clip_preprocess

    def _load_config(self):
        """Load the main config.yaml file"""
        config_path = "src/core/highlight_detection/config.yaml"
        logger.info(f"Loading configuration from {config_path}")
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("Configuration loaded.")
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}. Using defaults.")
            self.config = {}
    
    # =========================================================================
    # STEP 1: Download Video
    # =========================================================================
    def download_video(self, url: str) -> Path:
        """
        Download video from a URL
        
        Args:
            url: The public URL of the video to download
            
        Returns:
            Path: Location of the downloaded video file
            
        Example:
            video_path = processor.download_video("https://supabase.../video.mp4")
            # video_path = Path("/tmp/abc123.mp4")
        """
        logger.info(f"⬇️  Downloading video from {url}")
        
        # Create a temporary file to store the video
        temp_file = Path(tempfile.mktemp(suffix=".mp4"))
        
        # Download the video in chunks (better for large files)
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise error if download fails
        
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✅ Downloaded to {temp_file}")
        return temp_file
    
    # =========================================================================
    # STEP 2: Transcribe Video
    # =========================================================================
    def transcribe_video(self, video_path: Path, language: str = "auto", model_size: str = "base") -> list:
        """
        Convert video audio to text using Whisper AI.
        
        Args:
            video_path: Path to the video file
            language: Language code ('ko', 'en', 'auto' for automatic detection)
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            
        Returns:
            list: List of transcription segments
                  [{"start": 0.0, "end": 2.5, "text": "Hello world"}, ...]
        """
        logger.info(f"🎤 Transcribing {video_path} using '{model_size}' model...")
        
        # Import the transcription tools from your project
        from src.core.video_processing.video_to_audio import convert_video_to_audio
        from src.core.audio_processing.audio_to_text import transcribe_audio
        
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Step 1: Extract audio from video (video → audio.wav)
            audio_file_name = convert_video_to_audio(str(video_path), str(temp_dir))
            if not audio_file_name:
                raise RuntimeError("Audio conversion failed, convert_video_to_audio returned None.")
            
            audio_path = temp_dir / audio_file_name

            # Step 2: Transcribe audio to text (audio.wav → text + timestamps)
            transcribed_segments = transcribe_audio(str(audio_path), model_name=model_size)
            if not isinstance(transcribed_segments, list):
                raise RuntimeError(f"Transcription failed: {transcribed_segments}")

            # Step 3: Format output to match expected structure
            # Input format: [(text, (start_time, end_time)), ...]
            # Output format: [{"start": start, "end": end, "text": text}, ...]
            transcription = [
                {"start": start, "end": end, "text": text}
                for text, (start, end) in transcribed_segments
            ]

            logger.info(f"✅ Transcribed {len(transcription)} segments")
            return transcription
            
        finally:
            # Always clean up temporary files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

    # =========================================================================
    # STEP 3: Get Summarization (Title + Summary + Timestamps)
    # =========================================================================
    def get_summarization_from_video(self, video_path: Path):
        """
        Use LLM (Gemini) to analyze the video and generate:
        1. A catchy "hook title" for the short video
        2. A summary of the content
        3. Timestamps of the most important moments
        
        Args:
            video_path: Path to the video file
            
        Returns:
            tuple: (hook_title, summarized_segments, llm_timestamps)
                - hook_title: "Secrets 99% don't know" (catchy title)
                - summarized_segments: [(text, (start, end)), ...] (for subtitles)
                - llm_timestamps: [[start, end], ...] (highlight times)
        """
        logger.info("🧠 Running LLM summarization to get title, summary, and timestamps...")
        
        from src.core.summarization.video_to_summarization import video_to_summarization
        
        try:
            hook_title, summarized_segments, llm_timestamps = video_to_summarization(video_path)
            logger.info(f"✅ Summarization complete. Title: '{hook_title}'")
            return hook_title, summarized_segments, llm_timestamps
        except Exception as e:
            logger.error(f"Error in summarization pipeline: {e}", exc_info=True)
            return None, None, []

    # =========================================================================
    # STEP 4: Extract Highlights (EchoFusion Method)
    # =========================================================================
    def extract_highlights_echofusion(self, video_path: Path, llm_timestamps: list, 
                                       summarized_segments: str, options: dict) -> list:
        """
        Use the advanced EchoFusion pipeline to detect highlights.
        
        EchoFusion combines multiple signals:
        - Visual features (motion, scene changes)
        - Audio features (volume, speech patterns)
        - Text features (what's being said)
        
        This is more accurate than LLM-only but takes longer.
        
        Args:
            video_path: Path to the video
            llm_timestamps: Initial timestamps from LLM
            summarized_segments: Text summary from LLM
            options: Processing options from the user
            
        Returns:
            list: [{"start": 0.0, "end": 10.0, "score": 0.95}, ...]
        """
        logger.info("🎬 Extracting highlights with EchoFusion...")
        
        from src.core.highlight_detection.highlight_pipeline import run_echofusion

        # Get fusion weights from options or use defaults from config
        fusion_cfg = self.config.get("fusion", {})
        w_hd = options.get("w_hd", fusion_cfg.get("w_hd", 0.55))      # Visual weight
        w_txt = options.get("w_txt", fusion_cfg.get("w_txt", 0.45))   # Text weight
        w_aud = options.get("w_aud", fusion_cfg.get("w_aud", 0.0))    # Audio weight
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

        # Convert predictions to the format expected by the rest of the pipeline
        # Input format: [(start, end, score, rank), ...]
        # Output format: [{"start": start, "end": end, "score": score}, ...]
        highlights = [
            {"start": start, "end": end, "score": score} 
            for start, end, score, rank in predictions
        ]
        
        logger.info(f"✅ Found {len(highlights)} highlights via EchoFusion")
        return highlights

    # =========================================================================
    # STEP 5: Create Summary Video (Cut and Concatenate)
    # =========================================================================
    def create_summary_video(self, video_path: Path, highlights: list, output_path: Path):
        """
        Cut the highlight segments from the original video and combine them.
        
        Think of it like making a "best moments" compilation:
        1. Cut out each highlight segment
        2. Glue them together in order
        
        Args:
            video_path: Original video
            highlights: List of highlight timestamps [{"start": 0, "end": 10}, ...]
            output_path: Where to save the summary video
        """
        logger.info("✂️  Creating summary video...")

        if not highlights:
            logger.warning("No highlights provided. Cannot create summary video.")
            return None

        from src.core.video_processing.video_processor import cut_video_by_timestamps

        # Convert highlights to the format expected by cut_video_by_timestamps
        # Input: [{"start": 0, "end": 10}, ...]
        # Output: [(0, 10), ...]
        timestamps = [(h["start"], h["end"]) for h in highlights]

        cut_video_by_timestamps(
            video_path=str(video_path), 
            timestamps=timestamps, 
            output_path=str(output_path)
        )

        logger.info(f"✅ Summary video created: {output_path}")
        return output_path

    # =========================================================================
    # STEP 6: Add Subtitles
    # =========================================================================
    def add_subtitles(self, video_path: Path, summarized_segments: list, output_path: Path) -> Path:
        """
        Burn subtitles (captions) into the video.
        
        This takes the transcription and "burns" (permanently adds) the text
        onto the video so viewers can read what's being said.
        
        IMPORTANT: The timestamps need to be "remapped" because the summary video
        is shorter than the original. For example:
        - Original video: Segment at 30-35 seconds
        - Summary video: That same segment might now be at 0-5 seconds
        
        Args:
            video_path: Path to the summary video (already cut)
            summarized_segments: Original transcription [(text, (start, end)), ...]
            output_path: Where to save the subtitled video
            
        Returns:
            Path: Path to the subtitled video
        """
        logger.info("💬 Adding subtitles to video...")
        
        from src.core.subtitles.subtitles import burn_subtitles, remap_subtitles
        
        # Create a temporary directory for subtitle processing
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Step 1: Remap the subtitle timestamps to match the new (shorter) video
            # Original: [(text, (30.0, 35.0)), ...] 
            # Remapped: [(text, (0.0, 5.0)), ...]  
            remapped_segments = remap_subtitles(summarized_segments)
            logger.info(f"Remapped {len(remapped_segments)} subtitle segments")
            
            # Step 2: Copy the input video to temp directory
            # (burn_subtitles expects the video in a specific location)
            import shutil
            temp_video_name = "input_video.mp4"
            temp_video_path = temp_dir / temp_video_name
            shutil.copy(str(video_path), str(temp_video_path))
            
            # Step 3: Burn the subtitles into the video
            subtitled_video = burn_subtitles(
                file_name=temp_video_name,
                summarized_segments=remapped_segments,
                video_path=str(temp_dir),
                output_path=str(temp_dir),
                burn_in=True  # Permanently burn subtitles (not as separate track)
            )
            
            # Step 4: Copy the result to the final output path
            shutil.copy(subtitled_video, str(output_path))
            
            logger.info(f"✅ Subtitles added: {output_path}")
            return output_path
            
        finally:
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    # =========================================================================
    # STEP 7: Convert to Vertical Format
    # =========================================================================
    def convert_to_vertical(self, video_path: Path, output_path: Path, 
                            crop_method: str = "center") -> Path:
        """
        Convert a horizontal (16:9) video to vertical (9:16) for Shorts/Reels/TikTok.
        
        Two crop methods are available:
        - "center": Crops the center portion (loses sides of the video)
        - "blur": Keeps full video in center with blurred background filling the sides
        
        Args:
            video_path: Input video (usually 16:9 horizontal)
            output_path: Where to save the vertical video
            crop_method: "center" or "blur"
            
        Returns:
            Path: Path to the vertical video
        """
        logger.info(f"📱 Converting to vertical (9:16) format using '{crop_method}' method...")
        
        from src.core.video_processing.video_exporter import export_social_media_vertical_video
        
        export_social_media_vertical_video(
            input_path=str(video_path),
            output_path=str(output_path),
            resolution="1080x1920",  # Standard vertical resolution
            bitrate="15M",           # High quality bitrate
            crop_method=crop_method
        )
        
        logger.info(f"✅ Vertical video created: {output_path}")
        return output_path

    # =========================================================================
    # STEP 8: Upload to Supabase Storage
    # =========================================================================
    def upload_to_supabase(self, file_path: Path, bucket: str, destination: str) -> str:
        """
        Upload a file to Supabase Storage and get its public URL.
        
        Args:
            file_path: Local file to upload
            bucket: Supabase storage bucket name ("outputs", "videos", etc.)
            destination: Path within the bucket ("job123/summary.mp4")
            
        Returns:
            str: Public URL of the uploaded file
        """
        import mimetypes
        from supabase import create_client
        
        # Determine the file's MIME type (video/mp4, image/jpeg, etc.)
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        # Get Supabase credentials from environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        
        logger.info(f"⬆️  Uploading to Supabase: {bucket}/{destination}")
        
        # Create Supabase client and upload
        supabase = create_client(supabase_url, supabase_key)

        with open(file_path, 'rb') as f:
            response = supabase.storage.from_(bucket).upload(
                destination,
                f,
                file_options={"content-type": mime_type}
            )
        
        # Get the public URL for the uploaded file
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
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return False

        try:
            import subprocess
            
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
# GLOBAL PROCESSOR INSTANCE
# =============================================================================
# This is created once when the server starts and reused for all requests
# (this is called "warm start" - makes subsequent requests faster)
processor = VideoProcessor()


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================
def process_video(job):
    """
    Main video processing function called by RunPod.
    
    This is the "orchestrator" that calls all the other functions in order.
    
    The job input should look like this:
    {
        "input": {
            "job_id": "abc123",
            "video_url": "https://supabase.../video.mp4",
            "webhook_url": "https://your-backend.com/webhook",
            "options": {
                "method": "echofusion",  // or "llm_only"
                "language": "auto",
                "subtitle": true,         
                "vertical": true,         
                "crop_method": "center"   
            }
        }
    }
    """
    # Extract input data
    job_input = job.get("input", {})
    webhook_url = None
    job_id = None
    
    # Keep track of temporary files for cleanup
    temp_files = []

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
        whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
        transcription = processor.transcribe_video(
            video_path,
            language=options.get('language', 'auto'),
            model_size=whisper_model_size
        )
        
        # ---------------------------------------------------------------------
        # STEP 3: Get LLM summarization (title, summary, initial timestamps)
        # ---------------------------------------------------------------------
        hook_title, summarized_segments, llm_timestamps = processor.get_summarization_from_video(video_path)
        
        if not llm_timestamps:
            raise RuntimeError("Failed to generate timestamps from LLM summarization.")
        
        # ---------------------------------------------------------------------
        # STEP 4: Extract highlights (LLM-only or EchoFusion)
        # ---------------------------------------------------------------------
        method = options.get('method', 'echofusion')
        logger.info(f"Using highlight extraction method: {method}")

        if method == 'llm_only':
            logger.info("💬 Using timestamps directly from LLM summarization...")
            highlights = [{"start": start, "end": end} for start, end in llm_timestamps]
        else:
            # Use the more advanced EchoFusion method
            highlights = processor.extract_highlights_echofusion(
                video_path, llm_timestamps, summarized_segments, options
            )

        # ---------------------------------------------------------------------
        # STEP 5: Create the summary video (cut and concatenate highlights)
        # ---------------------------------------------------------------------
        summary_video_path = Path(tempfile.mkstemp(suffix=".mp4")[1])
        temp_files.append(summary_video_path)
        processor.create_summary_video(video_path, highlights, summary_video_path)
        
        # This will be the "current" video that we apply transformations to
        current_video_path = summary_video_path

        # ---------------------------------------------------------------------
        # STEP 6: Add subtitles if requested
        # ---------------------------------------------------------------------
        if options.get('subtitle', False) and summarized_segments:
            logger.info("📝 Subtitle option enabled - adding subtitles...")
            
            subtitled_video_path = Path(tempfile.mkstemp(suffix="_subtitled.mp4")[1])
            temp_files.append(subtitled_video_path)
            
            processor.add_subtitles(
                video_path=current_video_path,
                summarized_segments=summarized_segments,
                output_path=subtitled_video_path
            )
            
            # Update current video to the subtitled version
            current_video_path = subtitled_video_path
        else:
            logger.info("📝 Subtitle option: disabled or no segments available")

        # ---------------------------------------------------------------------
        # STEP 7: Convert to vertical format if requested
        # ---------------------------------------------------------------------
        if options.get('vertical', False):
            logger.info("📱 Vertical option enabled - converting to 9:16...")
            
            vertical_video_path = Path(tempfile.mkstemp(suffix="_vertical.mp4")[1])
            temp_files.append(vertical_video_path)
            
            crop_method = options.get('crop_method', 'center')
            processor.convert_to_vertical(
                video_path=current_video_path,
                output_path=vertical_video_path,
                crop_method=crop_method
            )
            
            # Update current video to the vertical version
            current_video_path = vertical_video_path
        else:
            logger.info("📱 Vertical option: disabled")

        # ---------------------------------------------------------------------
        # STEP 8: Upload the final video to Supabase
        # ---------------------------------------------------------------------
        result_url = processor.upload_to_supabase(
            current_video_path,
            bucket="outputs",
            destination=f"{job_id}/summary.mp4"
        )
        
        # ---------------------------------------------------------------------
        # STEP 9: Send success webhook to backend
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
                    "subtitle": options.get('subtitle', False),
                    "vertical": options.get('vertical', False)
                }
            })
        
        # ---------------------------------------------------------------------
        # CLEANUP: Remove temporary files
        # ---------------------------------------------------------------------
        for temp_file in temp_files:
            try:
                if temp_file.exists():
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
            "transcription": transcription[:5],  # Return first 5 segments as preview
            "highlights_count": len(highlights),
            "hook_title": hook_title,
            "options_applied": {
                "method": method,
                "subtitle": options.get('subtitle', False),
                "vertical": options.get('vertical', False)
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
    
    Input format:
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
    
    This function routes the job to the appropriate processor based on the 'task' field.
    
    Supported tasks:
    - "process_video": Full video processing pipeline
    - "generate_thumbnail": Generate thumbnail from video
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
            "error": f"Unknown task: {task}. Supported tasks: process_video, generate_thumbnail"
        }


# =============================================================================
# START THE RUNPOD SERVER
# =============================================================================
if __name__ == "__main__":
    if runpod:
        logger.info("🚀 Starting RunPod serverless handler...")
        runpod.serverless.start({"handler": handler})
    else:
        logger.info("Running in local test mode (RunPod not available)")
        