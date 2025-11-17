# --- Path setup for utils import ---
import sys
import os
import pathlib
import json
import argparse

# Add the project root to the Python path to allow importing from 'utils'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End Path setup ---

from core.highlight_detection.highlight_pipeline import run_echofusion
from core.summarization.video_to_summarization import video_to_summarization

# Usage
# python src/evaluation/run.py -i /path/to/video/folder

def batch_run_echofusion(video_folder: str):
    """
    Runs the echofusion highlight detection pipeline on all videos in a folder
    and saves the results to a single JSONL file.

    Args:
        video_folder (str): Path to the folder containing video files.
        output_jsonl_path (str): Path to the output JSONL file.
    """
    video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".flv")
    video_paths = [p for p in pathlib.Path(video_folder).glob("**/*") if p.suffix.lower() in video_extensions]

    print(f"Found {len(video_paths)} videos in '{video_folder}'.")

    output_jsonl_path = os.path.join(video_folder, "predictions.jsonl")

    count = 0
    with open(output_jsonl_path, "a") as outfile:
        for video_path in video_paths:
            print(f"\n--- ({count+1}/{len(video_paths)}) Processing: {video_path.name} ---")
            try:
                # [[start, end, score, rank], ...]
                print("-> Generating LLM timestamps ...")
                try:
                    _, summarized_segments, llm_timestamps = video_to_summarization(video_path)
                except Exception as e:
                    print(f"Error generating LLM timestamps for {video_path.name}: {e}")
                    summarized_segments, llm_timestamps = "", []    

                print("-> Running Echofusion ...")
                predictions = run_echofusion(
                    video_path,
                    summary=summarized_segments or "",
                    llm_timestamps=llm_timestamps
                )
                
                highlights = [{"start": p[0], "end": p[1], "score": p[2], "rank": p[3]} for p in predictions]

                result = {"video_name": video_path.name, "highlights": highlights}
                outfile.write(json.dumps(result) + "\n")
                outfile.flush()
                print(f"✅ Saved predictions for {video_path.name}")
                count += 1
            except Exception as e:
                print(f"❌ Failed to process {video_path.name}: {e}")

def main():
    
    parser = argparse.ArgumentParser(description="Make predictions for the given folder of videos.")
    parser.add_argument("-i", "--input_folder", type=str, required=True, help="Path to the folder with videos.")

    args = parser.parse_args()

    batch_run_echofusion(args.input_folder)

if __name__ == "__main__":
    main()