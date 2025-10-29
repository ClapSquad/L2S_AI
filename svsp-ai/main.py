import uuid
from utils.video_to_summarization import video_to_summarization
from utils.logging_initialization import initialize_logging
from utils.video_processor import cut_video_by_timestamps
from utils.video_exporter import export_social_media_vertical_video
from utils.subtitles import burn_subtitles, remap_subtitles
import os, argparse, subprocess, logging, json

# Usage
# python main.py -f <video_file> [options]

# To run the llm only method:
# python main.py -f input.mp4 --method llm --vertical_export

# To run the echofusion method:
# python main.py -f input.mp4 --method echofusion --title "Example Title"

def main():
    initialize_logging()
    parser = argparse.ArgumentParser(description="Video summarization script")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to input video")
    parser.add_argument("-v", "--vertical_export", action="store_true",
                        help="Exports a vertical (9:16) video optimized for social media.")
    parser.add_argument("-s", "--subtitles", action="store_true",
                        help="Burn caption into videos")

    # Highlight detection + LLM pipeline args
    parser.add_argument("--method", choices=["llm", "echofusion"], default="llm",
                        help="Choose summarization/highlight method.")
    parser.add_argument("--title", type=str, default="", help="Optional video title for echofusion.")
    parser.add_argument("--w_hd", type=float, default=0.45)
    parser.add_argument("--w_txt", type=float, default=0.35)
    parser.add_argument("--w_aud", type=float, default=0.20)
    parser.add_argument("--keep_seconds", type=float, default=60.0)

    args = parser.parse_args()

    video_path = args.file
    base_filename = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join("./assets", f"{base_filename}_{uuid.uuid4().hex[:6]}")
    os.makedirs(output_dir, exist_ok=True)

    # --- Summarization / Highlight detection ---
    hook_title, summarized_segments, llm_timestamps = video_to_summarization(video_path)

    if args.method == "llm":
        timestamps = llm_timestamps
    else:
        from utils.highlight_detection.highlight_pipeline import run_echofusion
        timestamps = run_echofusion(
            video_path,
            title=args.title or "",
            summary=hook_title or "",
            w_hd=args.w_hd, w_txt=args.w_txt, w_aud=args.w_aud,
            keep_seconds=args.keep_seconds
        )
        json.dump(timestamps, open(os.path.join(output_dir, f"{base_filename}_timestamps.json"), "w"), indent=2)

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
        remapped = remap_subtitles(summarized_segments)
        logging.debug(f"Remapped result => {remapped}")
        out_video = burn_subtitles(
            f"{hook_title}_reel.mp4" if args.vertical_export else f"{hook_title}_summary.mp4",
            remapped,
            output_dir,
            output_dir
        )
        logging.debug(f"Subtitled video generated at {out_video}")

if __name__ == "__main__":
    main()
