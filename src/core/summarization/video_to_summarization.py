from src.core.video_processing.video_to_audio import convert_video_to_audio
from src.core.audio_processing.audio_to_text import transcribe_audio
from src.core.summarization.boundary_alignment import align_timestamps_to_sentences
from src.core.summarization.coherence_validation import iterative_coherence_improvement
from .llm_client import call_gemini
import logging, shutil, os, json
from typing import List, Tuple

def video_to_summarization(VIDEO_PATH):
    CACHE_PATH = "./cache"

    try:
        print("-> Converting video to audio ...")
        audio_file = convert_video_to_audio(VIDEO_PATH, CACHE_PATH)
        if not audio_file:
            raise Exception("Audio conversion failed.")

        audio_path = os.path.join(CACHE_PATH, audio_file)
        print("-> Transcribing audio ...")
        transcribed_segments = transcribe_audio(audio_path)
        if not isinstance(transcribed_segments, list):
             raise Exception(f"Transcription failed: {transcribed_segments}")

        # Validate that transcription produced results
        if not transcribed_segments:
            raise Exception("Transcription returned empty results. The audio may contain no speech, be too quiet, or be corrupted.")

        logging.debug(f"Transcription result => {transcribed_segments}")
        logging.info(f"Transcribed {len(transcribed_segments)} segments, total duration: {transcribed_segments[-1][1][1]:.2f}s")

        prompt = f"""
            You are a video summarization assistant focused on creating COHERENT, concise highlights.

            Goal:
            Select the most important segments from the transcript to make a narratively coherent highlight summary whose
            TOTAL duration ≤ 60.0 seconds. Each segment must be SEMANTICALLY COMPLETE and self-contained.

            Inputs:
            - "Transcribed Segments" is a Python-like list of tuples: (text, (start_time, end_time)).
            - Times are in seconds (float).

            ⚠️ CRITICAL RULES FOR COHERENCE:
            1) NEVER cut in the middle of a sentence or thought.
            2) Each segment must START at the beginning of a sentence.
            3) Each segment must END at a natural pause (period, question mark, or clear thought completion).
            4) If a speaker says "Let me explain X" - include the explanation, not just the intro.
            5) Avoid segments that start with "and", "but", "so", "because" (mid-thought indicators).
            6) Avoid segments that end with incomplete phrases like "which means...", "so that...", "because of...".
            7) If an important point starts in one segment but completes in the next, MERGE them into a single timestamp range.

            Hard rules:
            1) Output valid JSON only (no prose), matching this schema:
            {{
                "timestamps": [ [start, end], ... ]    // non-overlapping, sorted by start ASC
            }}
            2) Each [start, end] must satisfy: 0 ≤ start < end, and (end - start) ≥ 3.0 seconds.
            3) Merge adjacent segments (< 1.5s gap) to maintain context and flow.
            4) Ensure TOTAL duration (sum over all segments) ≤ 60.0 seconds.
            5) Do NOT invent timestamps that are not present in input; you may extend start/end times slightly to merge adjacent segments.
            6) Keep language as-is (don’t translate text).
            7) If no meaningful segments exist, return {{ "timestamps": [] }}.

            Selection Priority (in order):
            1. Segments that are complete, standalone thoughts.
            2. Segments with concrete facts, steps, conclusions, or outcomes.
            3. Segments that introduce AND explain a concept (not just introduce).
            4. Segments with concrete examples or demonstrations.

            AVOID:
            - Segments that are questions without answers.
            - Introductory phrases without the content they introduce.
            - Conclusions without the reasoning that led to them.

            Output examples:
            OK → {{ "timestamps": [[0.50, 7.80], [12.00, 24.10], [45.00, 58.70]] }}
            OK (empty) → {{ "timestamps": [] }}

            Transcribed Segments:
            {transcribed_segments}
        """
        print("-> Generating summarization timestamps via LLM ...")
        summarization_result = call_gemini("gemini-2.5-flash", prompt, as_json=True)
        summary_json = summarization_result.get('json')
        logging.debug(f"Summarization result => {summary_json}")

        if not summary_json or "timestamps" not in summary_json:
            raise Exception(f"Failed to get valid timestamps from LLM. Response: {summary_json}")

        timestamps: List[Tuple[float, float]] = summary_json["timestamps"]

        # Validate that LLM returned meaningful timestamps
        if not timestamps:
            raise Exception(
                "LLM returned empty timestamps. This could mean:\n"
                "  1. The transcribed content has no meaningful segments\n"
                "  2. The LLM couldn't identify important content\n"
                "  3. The video content may be too repetitive or low-quality\n"
                f"  Transcription preview: {str(transcribed_segments[:3])[:200]}..."
            )
        
        # Align timestamps to sentence boundaries
        print("-> Aligning timestamps to sentence boundaries ...")
        timestamps = align_timestamps_to_sentences(timestamps, transcribed_segments)
        logging.info(f"Adjusted timestamps for sentence alignment: {timestamps}")

        # Iteratively improve coherence
        print("-> Validating and improving narrative coherence...")
        timestamps = iterative_coherence_improvement(timestamps, transcribed_segments)
        logging.info(f"Final timestamps after coherence validation: {timestamps}")

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
        print("-> Generating hook title ...")
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
            print("-> Cleaning up cache ...")
            shutil.rmtree(CACHE_PATH)
            logging.debug(f"Removed cache folder: {CACHE_PATH}")
