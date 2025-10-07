from utils.video_to_summarization import video_to_summarization
from utils.logging_initialization import initialize_logging
from utils.video_processor import cut_video_by_timestamps
import os

def main():
    initialize_logging()
    VIDEO_PATH = r"/home/gianella/datasets/test_videos/How to Knit the Box Stitch.webm"
    
    # Define output path for the summarized video
    output_dir = "./output"
    os.makedirs(output_dir, exist_ok=True)
    base_filename = os.path.splitext(os.path.basename(VIDEO_PATH))[0]
    SUMMARIZED_VIDEO_PATH = os.path.join(output_dir, f"{base_filename}_summary.mp4")

    summary_text, timestamps = video_to_summarization(VIDEO_PATH)

    cut_video_by_timestamps(VIDEO_PATH, timestamps, SUMMARIZED_VIDEO_PATH)

    print("--- Video Summary ---")
    print(summary_text)

if __name__ == '__main__':
    main()