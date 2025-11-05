from .llm_client import call_gemini
import logging, shutil, os, json, ast

def video_to_summarization(VIDEO_PATH):
    CACHE_PATH = "./cache"

    try:
        filename = os.path.basename(VIDEO_PATH)
        video_id = os.path.splitext(filename)[0]

        transcribed_segments = None
        with open(r"transcribed_data.jsonl", "r") as f:
            for line in f:
                data = json.loads(line)
                if data.get("id") == video_id:
                    transcribed_segments = ast.literal_eval(data["text"])
                    break

        transcribed_segments = [
            (seg[0].strip(), (float(seg[1][0]), float(seg[1][1])))
            for seg in transcribed_segments
        ]

        timestamps = None
        with open(r"summarized_results.jsonl", "r") as f:
            for line in f:
                data = json.loads(line)
                if data.get("id") == video_id:
                    timestamps = data["result"]["timestamps"]
                    break

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
