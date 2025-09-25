from utils.video_to_audio import convert_video_to_audio
from utils.audio_to_text import transcribe_audio
import logging, shutil, os

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename="log.log",
                    level=logging.DEBUG)
logging.debug("Logging started.")


def main():
    # VIDEO_PATH = "./examples/A Great Example For A 30 Seconds B2B Explainer Video - Multi lock.mp4"
    VIDEO_PATH = "{target video path}"
    CACHE_PATH = "./cache"

    audio_file = convert_video_to_audio(VIDEO_PATH, CACHE_PATH)

    audio_path = os.path.join(CACHE_PATH, audio_file)
    text = transcribe_audio(audio_path)

    print(text)

    if os.path.exists(CACHE_PATH):
        shutil.rmtree(CACHE_PATH)
        logging.debug(f"Removed cache folder: {CACHE_PATH}")


if __name__ == '__main__':
    main()
