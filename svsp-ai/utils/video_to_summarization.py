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

        timestamps: List[Tuple[float, float]] = summary_json["timestamps"]
        logging.info(f"Parsed timestamps for cutting: {timestamps}")

        # Extract text for the summarized segments
        summarized_text = " ".join(
            text for text, (start, end) in transcribed_segments
            if any(ts_start <= start and end <= ts_end for ts_start, ts_end in timestamps)
        )
        logging.debug(f"Summarized text for title generation: {summarized_text}")

        # Generate a hook title based on the summarized text
        title_prompt = f"""
        You are a viral content creator.
        Based on the following video transcript, generate a short, catchy, and engaging hook title for a social media video.
        The title should be at most 10 words.

        Hard constraints:
        - Use only letters (A–Z, a–z), numbers (0–9), and spaces.
        - Do NOT use punctuation, emojis, symbols, or special characters.
        - Do NOT put the title in quotes or code blocks.
        - Output a single line containing ONLY the title text.

        Transcript:
        {summarized_text}
        """
        title_result = call_gemini("gemini-2.5-flash", title_prompt)
        hook_title = title_result.get('text', "Video Summary").strip()
        logging.info(f"Generated hook title: {hook_title}")

        if os.path.exists(CACHE_PATH):
            shutil.rmtree(CACHE_PATH)
            logging.debug(f"Removed cache folder: {CACHE_PATH}")

        summarized_segments = []
        for (text, (seg_start, seg_end)) in transcribed_segments:
            for (ts_start, ts_end) in timestamps:
                overlap = min(seg_end, ts_end) - max(seg_start, ts_start)
                if overlap > 0.5:  # 일정 부분 이상 겹치면 포함
                    summarized_segments.append((text, (seg_start, seg_end)))
                    break

        # The raw text response is no longer the primary source of data, but can be returned for logging/display
        return hook_title, summarized_segments, timestamps

    finally:
        if os.path.exists(CACHE_PATH):
            logging.debug(f"Removed cache folder: {CACHE_PATH}")
