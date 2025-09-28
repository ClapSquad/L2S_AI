from video_to_audio import convert_video_to_audio
from audio_to_text import transcribe_audio
from llm_client import call_gemini
import logging, shutil, os


def video_to_summarization(VIDEO_PATH):
    CACHE_PATH = "./cache"

    audio_file = convert_video_to_audio(VIDEO_PATH, CACHE_PATH)

    audio_path = os.path.join(CACHE_PATH, audio_file)
    text = transcribe_audio(audio_path)
    logging.debug(f"Transcription result => {text}")

    prompt = f"This is sentence with corresponding timestamp. {str(text)} Please pick important sentence and remove the rest. Try to make total length maximum up to 1 minute. Right your answer in a same format"
    summarization = call_gemini("gemini-2.5-flash", prompt)
    logging.debug(f"summarization result => {summarization['text']}")

    if os.path.exists(CACHE_PATH):
        shutil.rmtree(CACHE_PATH)
        logging.debug(f"Removed cache folder: {CACHE_PATH}")

    return summarization['text']
