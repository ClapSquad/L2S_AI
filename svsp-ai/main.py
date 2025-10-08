from utils.video_to_summarization import video_to_summarization
from utils.logging_initialization import initialize_logging
from utils.video_processor import cut_video_by_timestamps
import os
import argparse


def main():
    initialize_logging()
    parser = argparse.ArgumentParser(description="Video summarization script")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the input video file")
    args = parser.parse_args()

    VIDEO_PATH = args.file
    OUTPUT_PATH = "./output"
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    base_filename = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
    SUMMARIZED_VIDEO_PATH = os.path.join(OUTPUT_PATH, f"{base_filename}_summary.mp4")

    summary_text, timestamps = video_to_summarization(VIDEO_PATH)
    cut_video_by_timestamps(VIDEO_PATH, timestamps, SUMMARIZED_VIDEO_PATH)


if __name__ == '__main__':
    main()
