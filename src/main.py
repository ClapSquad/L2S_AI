from pathlib import Path
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import argparse
import subprocess
import logging
import json
import uuid

from src.core.summarization.video_to_summarization import video_to_summarization
from src.core.video_processing.video_processor import cut_video_by_timestamps
from src.core.video_processing.video_exporter import export_social_media_vertical_video
from src.core.subtitles.subtitle_burner import burn_subtitles_complete_pipeline

from utils.logging_initialization import initialize_logging

# Usage
# python main.py -f <video_file> [options]

# To run the llm only method:
# python main.py -f input.mp4 --method llm --vertical_export

# To run the echofusion method:
# python src/main.py -f input.mp4 --method echofusion --title "Example Title"

def main():
    initialize_logging()
    parser = argparse.ArgumentParser(description="Video summarization script")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to input video")
    parser.add_argument("-v", "--vertical_export", action="store_true",
                        help="Exports a vertical (9:16) video optimized for social media.")
    parser.add_argument("-s", "--subtitles", action="store_true",
                        help="Burn karaoke-style captions into videos.")
    parser.add_argument("--subtitle_style", type=str, default="dynamic",
                        choices=["simple1", "simple2", "simple3", "casual", "dynamic"],
                        help="Subtitle style for burning.")
    parser.add_argument("--whisper_model", type=str, default="base",
                        help="Whisper model for transcription (e.g., tiny, base, small).")


    # Highlight detection + LLM pipeline args
    parser.add_argument("--method", choices=["llm", "echofusion"], default="llm",
                        help="Choose summarization/highlight method.")
    parser.add_argument("--title", type=str, default="", help="Optional video title for echofusion.")
    parser.add_argument("--w_hd", type=float, default=0.55)
    parser.add_argument("--w_txt", type=float, default=0.45)
    parser.add_argument("--w_aud", type=float, default=0.00)
    parser.add_argument("--keep_seconds", type=float, default=60.0)

    args = parser.parse_args()

    video_path = args.file
    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join("assets", f"{base_filename}_{uuid.uuid4().hex[:6]}")
    os.makedirs(output_dir, exist_ok=True)

    # --- Summarization / Highlight detection ---
    try:
        hook_title, summarized_segments, llm_timestamps = video_to_summarization(video_path)
    except Exception as e:
        logging.error(f"Error in summarization pipeline: {e}")
        return

    if args.method == "llm":
        timestamps = llm_timestamps
    else:
        from src.core.highlight_detection.highlight_pipeline import run_echofusion
        predictions = run_echofusion(
            Path(video_path),
            title=args.title or "",
            summary=summarized_segments or "",
            llm_timestamps=llm_timestamps,
            w_hd=args.w_hd, w_txt=args.w_txt, w_aud=args.w_aud,
            keep_seconds=args.keep_seconds
        )
        timestamps = [[start, end] for start, end, score, rank in predictions]
        json.dump(predictions, open(os.path.join(output_dir, f"{base_filename}_timestamps.json"), "w"), indent=2)

    print(f"\n--- Completed summarization/highlight detection. Generated title: {hook_title} ---")
    print("Cutting timestamps...")
    # --- Create summarized video ---
    summarized_video_path = os.path.join(output_dir, f"{hook_title}_summary.mp4")
    cut_video_by_timestamps(video_path, timestamps, summarized_video_path)

    # --- Optional vertical export ---
    if args.vertical_export:
        vertical_export_path = os.path.join(output_dir, f"{hook_title}_reel.mp4")
        try:
            print("\n--- Vertical Export ---")
            export_social_media_vertical_video(
                input_path=summarized_video_path,
                output_path=vertical_export_path
            )
            print(f"\nCompleted. Final video: {vertical_export_path}")
        except subprocess.CalledProcessError:
            print(f"\nVertical export step failed (FFmpeg Command Error). Check details above.")
        except FileNotFoundError:
            print(f"\nVertical export step failed (File Not Found). Check FFmpeg installation.")
        except ValueError as e:
            print(f"\nVertical export step failed (Invalid Parameter): {e}")
        except Exception as e:
            print(f"\nVertical export step failed (Unexpected Error): {e}")

    # --- Optional subtitle burn ---
    if args.subtitles:
        print("\n--- Burning Karaoke-Style Subtitles ---")
        video_to_subtitle = vertical_export_path if args.vertical_export else summarized_video_path
        subtitled_output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(video_to_subtitle))[0]}_subtitled.mp4")

        try:
            burn_subtitles_complete_pipeline(
                video_path=video_to_subtitle,
                output_path=subtitled_output_path,
                style=args.subtitle_style,
                whisper_model=args.whisper_model,
                # Assuming vertical video dimensions if that option is chosen
                video_width=1080 if args.vertical_export else 1920, # Default to horizontal if not vertical
                video_height=1920 if args.vertical_export else 1080
            )
        except Exception as e:
            logging.error(f"Failed to burn subtitles: {e}")

    print(f"\nAll done! Check output folder: {output_dir}")

if __name__ == "__main__":
    main()