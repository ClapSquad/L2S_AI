from .video_to_audio import convert_video_to_audio
from .audio_to_text import transcribe_audio
from .llm_client import call_gemini
import logging, shutil, os, json
from typing import List, Tuple


def video_to_summarization(VIDEO_PATH):
    CACHE_PATH = "./cache"

    try:
        audio_file = convert_video_to_audio(VIDEO_PATH, CACHE_PATH)
        if not audio_file:
            raise Exception("Audio conversion failed.")

        audio_path = os.path.join(CACHE_PATH, audio_file)
        transcribed_segments = transcribe_audio(audio_path)
        if not isinstance(transcribed_segments, list):
             raise Exception(f"Transcription failed: {transcribed_segments}")
        logging.debug(f"Transcription result => {transcribed_segments}")

        prompt = f"""
        You are a video summarization assistant.
        Given a list of transcribed segments with timestamps, select the most important segments to create a summary of up to 1 minute.
        Respond with a JSON object containing a single key "timestamps", which is a list of [start, end] arrays for the selected segments.

        Example Input:
        [('Hello world.', (0.5, 1.5)), ('This is a test.', (2.0, 3.0)), ('Another important segment.', (10.0, 12.5))]

        Example Output:
        {{ "timestamps": [ [0.5, 1.5], [10.0, 12.5] ] }}

        Transcribed Segments:
        {str(transcribed_segments)}
        """
        summarization_result = call_gemini("gemini-2.5-flash", prompt, as_json=True)
        summary_json = summarization_result.get('json')
        logging.debug(f"Summarization result => {summary_json}")

        if not summary_json or "timestamps" not in summary_json:
            raise Exception(f"Failed to get valid timestamps from LLM. Response: {summary_json}")

        timestamps = summary_json["timestamps"]
        logging.info(f"Parsed timestamps for cutting: {timestamps}")

        # The raw text response is no longer the primary source of data, but can be returned for logging/display
        return summarization_result['text'], timestamps

    finally:
        if os.path.exists(CACHE_PATH):
            logging.debug(f"Removed cache folder: {CACHE_PATH}")
