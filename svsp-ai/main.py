from utils.video_to_summarization import video_to_summarization
import logging, shutil, os

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename="log.log",
                    level=logging.DEBUG)
logging.debug("Logging started.")


def main():
    # VIDEO_PATH = "./examples/Kurzgesagt - Alcohol is AMAZING.mp4"
    VIDEO_PATH = "{target video path}"
    video_to_summarization(VIDEO_PATH)


if __name__ == '__main__':
    main()
