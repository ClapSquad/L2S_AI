from utils.video_to_audio import convert_video_to_audio
from utils.audio_to_text import transcribe_audio
from utils.llm_client import call_gemini
import logging, shutil, os

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename="log.log",
                    level=logging.DEBUG)
logging.debug("Logging started.")


def main():
    # VIDEO_PATH = "./examples/Kurzgesagt - Alcohol is AMAZING.mp4"
    VIDEO_PATH = "{target video path}"
    CACHE_PATH = "./cache"

    audio_file = convert_video_to_audio(VIDEO_PATH, CACHE_PATH)

    audio_path = os.path.join(CACHE_PATH, audio_file)
    text = transcribe_audio(audio_path)
    logging.debug(text)

    prompt = f"This is sentence with corresponding timestamp. {str(text)} Please pick important sentence and remove the rest. Try to make total length maximum up to 1 minute. Right your answer in a same format"
    res = call_gemini("gemini-2.5-flash", prompt)
    print(res['text'])

    if os.path.exists(CACHE_PATH):
        shutil.rmtree(CACHE_PATH)
        logging.debug(f"Removed cache folder: {CACHE_PATH}")


if __name__ == '__main__':
    main()
