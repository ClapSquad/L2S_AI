# to run this first you need to install whisper (also whisper requires ffmpeg)
# pip install openai-whisper
# sudo apt update && sudo apt install ffmpeg

# To use this script
# python audio_to_text.py example_file.mp3

import whisper
import argparse
import logging, os
from typing import List, Tuple

def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribes an audio file and returns a list of (text, (start, end)) tuples
    taken from Whisper's per-segment timestamps (seconds).

    Args:
        audio_path: Path to the audio file (.mp3, .wav, .m4a, etc.)
        model_name: Whisper model name ("tiny", "base", "small", "medium", "large")

    Returns:
        List of tuples: [(segment_text, (start_sec, end_sec)), ...]
        If file is missing or an error occurs, returns an empty list.
    """
    if not os.path.exists(audio_path):
        return f"Error: Audio file not found at '{audio_path}'."

    try:
        
        # Load a Whisper model. The first time this is run, it will download the model.
        # Model options: "tiny", "base", "small", "medium", "large"
        # 일단 choosing base because it has a good balance of speed and accuracy.

        logging.debug(f"Loading model ('{model_name}')...")
        model = whisper.load_model(model_name)
        logging.debug("Model loaded successfully.")

        logging.debug(f"Starting transcription for '{audio_path}'...")
        result = model.transcribe(audio_path)
        language = result["language"]   
        logging.debug(f"Detected language: {result.get('language')}")
        logging.debug("Transcription complete.")

        # transcribed_text = result["text"]
        # return transcribed_text

        # the segments key contains the segment-level timestamps
        segments = result.get("segments", [])

        tuples: List[Tuple[str, Tuple[float, float]]] = [
            (seg.get("text", "").strip(), (float(seg.get("start", 0.0)), float(seg.get("end", 0.0))))
            for seg in segments
        ]
        return tuples

    except Exception as e:
        return f"An error occurred during transcription: {e}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file to text using OpenAI's Whisper."
    )
    parser.add_argument(
        "audio_file", 
        type=str, 
        help="The path to the audio file to transcribe."
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default="base", 
        choices=["tiny", "base", "small", "medium", "large"],
        help="The Whisper model to use for transcription (default: base)."
    )
    
    args = parser.parse_args()

    # Call to the the transcription function
    text = transcribe_audio(args.audio_file, args.model)

    # Print the result
    print("\n--- Transcription Result ---")
    for tuple in text:
        print(tuple)
    print("--------------------------")
