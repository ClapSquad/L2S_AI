"""
Enhanced Subtitle Burner with Karaoke Support

This module handles the final step: burning subtitles into the video.

What does "burning" mean?
Think of it like permanently writing on a photo. Once subtitles are "burned"
into a video, they become part of the video image itself. You can't turn them
off like you can with YouTube's CC button - they're always visible.

Why burn subtitles?
- Social media platforms don't always support subtitle files
- Ensures consistent appearance across all devices
- Creates the professional look seen on TikTok/Reels

This module supports:
1. Simple SRT subtitles (basic white text)
2. ASS karaoke subtitles (animated, highlighted text)
3. Multiple visual styles matching the frontend
"""

import os
import subprocess
import logging
import tempfile
from typing import List, Tuple, Dict, Optional, Union
from pathlib import Path


# ============================================================================
# FFMPEG SUBTITLE BURNING
# ============================================================================

def burn_ass_subtitles(
    video_path: str,
    ass_path: str,
    output_path: str,
    fonts_dir: Optional[str] = None
) -> str:
    """
    Burn ASS subtitles into a video using FFmpeg.
    
    This is like printing text directly onto each frame of the video.
    FFmpeg reads the ASS file and renders the styled text.
    
    Args:
        video_path: Path to the input video
        ass_path: Path to the ASS subtitle file
        output_path: Where to save the output video
        fonts_dir: Optional directory containing custom fonts
    
    Returns:
        Path to the output video
    
    Technical note:
    FFmpeg uses the 'ass' filter which is part of libass.
    This filter interprets all ASS styling including:
    - Colors and outlines
    - Karaoke timing ({\k} tags)
    - Font changes
    - Positioning
    """
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # Build the filter string
    # Note: We need to escape special characters in the path for FFmpeg
    ass_path_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
    
    if fonts_dir:
        # Include custom fonts directory
        filter_str = f"ass={ass_path_escaped}:fontsdir={fonts_dir}"
    else:
        filter_str = f"ass={ass_path_escaped}"
    
    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",                          # Overwrite output file if exists
        "-i", video_path,              # Input video
        "-vf", filter_str,             # Video filter (burn subtitles)
        "-c:a", "copy",                # Copy audio without re-encoding
        "-c:v", "libx264",             # Use H.264 video codec
        "-preset", "fast",             # Encoding speed/quality tradeoff
        "-crf", "18",                  # Quality (lower = better, 18-23 is good)
        output_path
    ]
    
    logging.info(f"Burning ASS subtitles into video...")
    logging.info(f"  Input: {video_path}")
    logging.info(f"  Subtitles: {ass_path}")
    logging.info(f"  Output: {output_path}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"✅ Successfully created: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"Failed to burn subtitles: {e.stderr}")


def burn_srt_subtitles_styled(
    video_path: str,
    srt_path: str,
    output_path: str,
    style: str = "simple1"
) -> str:
    """
    Burn SRT subtitles with custom styling using FFmpeg's subtitles filter.
    
    While SRT doesn't support styling natively, FFmpeg allows us to
    apply custom styles when burning subtitles.
    
    This is useful for simple, non-karaoke subtitles that still look good.
    
    Args:
        video_path: Path to input video
        srt_path: Path to SRT subtitle file
        output_path: Where to save output video
        style: Style name ("simple1", "simple2", "simple3", "casual")
    
    Returns:
        Path to output video
    """
    
    # Define force_style parameters for each style
    # Format: font family, font size, colors in ASS format
    style_params = {
        "simple1": {
            "FontName": "Arial",
            "FontSize": "24",
            "PrimaryColour": "&H00FFFFFF",  # White
            "OutlineColour": "&H00000000",  # Black outline
            "Outline": "2",
            "Shadow": "0",
            "Alignment": "2",  # Bottom center
            "MarginV": "60"
        },
        "simple2": {
            "FontName": "Arial",
            "FontSize": "22",
            "PrimaryColour": "&H00000000",  # Black text
            "BackColour": "&H80FFFFFF",     # Semi-transparent white bg
            "BorderStyle": "3",             # Opaque box
            "Alignment": "2",
            "MarginV": "60"
        },
        "simple3": {
            "FontName": "Arial",
            "FontSize": "22",
            "PrimaryColour": "&H00FFFFFF",  # White text
            "BackColour": "&H80000000",     # Semi-transparent black bg
            "BorderStyle": "3",
            "Alignment": "2",
            "MarginV": "60"
        },
        "casual": {
            "FontName": "Arial",
            "FontSize": "26",
            "PrimaryColour": "&H00FFFFFF",
            "OutlineColour": "&H00000000",
            "Outline": "3",
            "Shadow": "2",
            "Alignment": "2",
            "MarginV": "60"
        }
    }
    
    params = style_params.get(style, style_params["simple1"])
    
    # Build force_style string
    force_style = ",".join(f"{k}={v}" for k, v in params.items())
    
    # Escape the SRT path for FFmpeg
    srt_path_escaped = srt_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    
    filter_str = f"subtitles={srt_path_escaped}:force_style='{force_style}'"
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        output_path
    ]
    
    logging.info(f"Burning SRT subtitles with style '{style}'...")
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"✅ Successfully created: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg error: {e.stderr}")
        raise RuntimeError(f"Failed to burn subtitles: {e.stderr}")


# ============================================================================
# HIGH-LEVEL INTEGRATION FUNCTION
# ============================================================================

def burn_karaoke_subtitles(
    video_path: str,
    words: List[Dict],
    output_path: str,
    style: str = "dynamic",
    video_width: int = 1080,
    video_height: int = 1920,
    words_per_line: int = 3,
    karaoke_mode: str = "word_by_word",
    cleanup_temp: bool = True
) -> str:
    """
    Complete pipeline: Generate ASS from words and burn into video.
    
    This is the main function you'll want to use in your pipeline.
    It handles everything from word timing data to final video.
    
    Args:
        video_path: Input video file
        words: Word timing data [{"word": "Hello", "start": 0.0, "end": 0.4}, ...]
        output_path: Where to save the final video
        style: Visual style ("simple1", "simple2", "simple3", "casual", "dynamic")
        video_width: Video width in pixels
        video_height: Video height in pixels
        words_per_line: How many words to show at once
        karaoke_mode: Animation type ("highlight", "fill", "word_by_word")
        cleanup_temp: Whether to delete temporary ASS file after burning
    
    Returns:
        Path to the output video with burned subtitles
    
    Example:
        words = [
            {"word": "Welcome", "start": 0.0, "end": 0.5},
            {"word": "to", "start": 0.6, "end": 0.8},
            {"word": "my", "start": 0.9, "end": 1.1},
            {"word": "channel", "start": 1.2, "end": 1.8}
        ]
        
        output = burn_karaoke_subtitles(
            "video.mp4",
            words,
            "video_with_subs.mp4",
            style="dynamic"
        )
    """
    from src.core.subtitles.karaoke_subtitles import generate_karaoke_ass
    
    # Create temporary ASS file
    temp_dir = tempfile.mkdtemp()
    ass_path = os.path.join(temp_dir, "karaoke.ass")
    
    try:
        # Step 1: Generate ASS file from word timings
        logging.info(f"Generating ASS subtitle file...")
        generate_karaoke_ass(
            words=words,
            output_path=ass_path,
            style_type=style,
            video_width=video_width,
            video_height=video_height,
            words_per_line=words_per_line,
            karaoke_mode=karaoke_mode
        )
        
        # Step 2: Burn ASS subtitles into video
        logging.info(f"Burning subtitles into video...")
        result = burn_ass_subtitles(
            video_path=video_path,
            ass_path=ass_path,
            output_path=output_path
        )
        
        return result
        
    finally:
        # Cleanup temporary files
        if cleanup_temp:
            try:
                os.remove(ass_path)
                os.rmdir(temp_dir)
            except:
                pass


def burn_subtitles_complete_pipeline(
    video_path: str,
    output_path: str,
    style: str = "dynamic",
    whisper_model: str = "base",
    video_width: int = 1080,
    video_height: int = 1920,
    words_per_line: int = 3,
    karaoke_mode: str = "word_by_word",
    extract_audio: bool = True
) -> str:
    """
    Complete end-to-end pipeline: Video → Transcribe → Karaoke Subtitles.
    
    This is the ultimate convenience function that does everything:
    1. Extracts audio from video
    2. Transcribes with word-level timestamps
    3. Generates karaoke ASS file
    4. Burns subtitles into video
    
    Args:
        video_path: Input video file
        output_path: Where to save the final video
        style: Visual style
        whisper_model: Whisper model size
        video_width: Video width
        video_height: Video height
        words_per_line: Words per subtitle line
        karaoke_mode: Animation type
        extract_audio: If True, extract audio from video first
    
    Returns:
        Path to the output video
    """
    from src.core.audio_processing.audio_to_text_enhanced import transcribe_for_karaoke
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Step 1: Extract audio if needed
        if extract_audio:
            audio_path = os.path.join(temp_dir, "audio.mp3")
            logging.info(f"Extracting audio from video...")
            
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",                    # No video
                "-acodec", "libmp3lame",  # MP3 codec
                "-q:a", "2",              # Quality
                audio_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            audio_path = video_path
        
        # Step 2: Transcribe with word timestamps
        logging.info(f"Transcribing audio with word-level timestamps...")
        words = transcribe_for_karaoke(audio_path, whisper_model)
        
        if isinstance(words, str):  # Error
            raise RuntimeError(f"Transcription failed: {words}")
        
        if not words:
            raise RuntimeError("No words detected in audio")
        
        logging.info(f"Detected {len(words)} words")
        
        # Step 3: Generate and burn subtitles
        result = burn_karaoke_subtitles(
            video_path=video_path,
            words=words,
            output_path=output_path,
            style=style,
            video_width=video_width,
            video_height=video_height,
            words_per_line=words_per_line,
            karaoke_mode=karaoke_mode
        )
        
        return result
        
    finally:
        # Cleanup temp files
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


# ============================================================================
# LEGACY COMPATIBILITY
# ============================================================================

def remap_subtitles(summarized_segments):
    """
    Remap subtitle timestamps for concatenated videos.
    
    When you cut and join video segments, the timestamps need to be
    recalculated to match the new video timeline.
    
    This is the same function from your existing code, preserved for
    backward compatibility.
    """
    remapped = []
    current_time = 0.0

    for text, (orig_start, orig_end) in summarized_segments:
        seg_len = orig_end - orig_start
        new_start = current_time
        new_end = current_time + seg_len
        remapped.append((text, (new_start, new_end)))
        current_time = new_end

    return remapped


def seconds_to_srt_time(t: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    milliseconds = int(round((t - int(t)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def segments_to_srt(segments: List[Tuple[str, Tuple[float, float]]], srt_path: str):
    """Generate an SRT file from segment data (legacy format)"""
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (text, (start, end)) in enumerate(segments, start=1):
            start_ts = seconds_to_srt_time(start)
            end_ts = seconds_to_srt_time(end)
            text = text.replace("\r\n", "\n").strip()
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{text}\n\n")


def burn_subtitles_legacy(
    file_name: str,
    summarized_segments: List[Tuple[str, Tuple[float, float]]],
    video_path: str,
    output_path: str,
    burn_in: bool = True
) -> str:
    """
    Legacy function for backward compatibility with existing code.
    
    This maintains the same interface as your current burn_subtitles function
    in src/core/subtitles/subtitles.py
    """
    input_path = os.path.join(video_path, file_name)

    # Generate SRT file
    srt_filename = f"{os.path.splitext(file_name)[0]}.srt"
    srt_path = os.path.join(output_path, srt_filename)
    segments_to_srt(summarized_segments, srt_path)

    # Burn subtitles
    out_video = os.path.join(output_path, f"{os.path.splitext(file_name)[0]}_subtitled.mp4")

    if burn_in:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"subtitles={srt_path}", "-c:a", "copy", out_video]
    else:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-i", srt_path, "-c", "copy", "-c:s", "mov_text", out_video]

    subprocess.run(cmd, check=True)

    return out_video


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Burn karaoke-style subtitles into video"
    )
    parser.add_argument(
        "video",
        type=str,
        help="Input video file"
    )
    parser.add_argument(
        "-w", "--words",
        type=str,
        help="JSON file with word timing data (if not provided, will transcribe)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output video path"
    )
    parser.add_argument(
        "--style",
        type=str,
        default="dynamic",
        choices=["simple1", "simple2", "simple3", "casual", "dynamic"],
        help="Subtitle style"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        help="Whisper model for transcription"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="word_by_word",
        choices=["highlight", "fill", "word_by_word"],
        help="Karaoke animation mode"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(args.video)[0]
        output_path = f"{base}_karaoke.mp4"
    
    if args.words:
        # Use provided word data
        with open(args.words, 'r', encoding='utf-8') as f:
            words = json.load(f)
        
        result = burn_karaoke_subtitles(
            video_path=args.video,
            words=words,
            output_path=output_path,
            style=args.style,
            karaoke_mode=args.mode
        )
    else:
        # Full pipeline with transcription
        result = burn_subtitles_complete_pipeline(
            video_path=args.video,
            output_path=output_path,
            style=args.style,
            whisper_model=args.model,
            karaoke_mode=args.mode
        )
    
    print(f"\n✅ Output saved to: {result}")