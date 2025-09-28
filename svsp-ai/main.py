from utils.video_to_summarization import video_to_summarization
from utils.logging_initialization import initialize_logging


def main():
    initialize_logging()
    # VIDEO_PATH = "./examples/Kurzgesagt - Alcohol is AMAZING.mp4"
    VIDEO_PATH = "{target video path}"
    video_to_summarization(VIDEO_PATH)


if __name__ == '__main__':
    main()
