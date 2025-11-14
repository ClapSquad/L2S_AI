# to run this first you need to install whisper (also whisper requires ffmpeg)
# pip install faster-whisper

# To use this script
# python audio_to_text.py example_file.mp3

import argparse
import logging, os
from typing import List, Tuple, Union
from faster_whisper import WhisperModel

def transcribe_audio(audio_path: str, model_name: str = "base") -> Union[List[Tuple[str, Tuple[float, float]]], str]:
    """
    Transcribes an audio file and returns a list of (text, (start, end)) tuples
    taken from Whisper's per-segment timestamps (seconds).

    Args:
        audio_path: Path to the audio file (.mp3, .wav, .m4a, etc.)
        model_name: Whisper model name ("tiny", "base", "small", "medium", "large")
                  See https://github.com/guillaumekln/faster-whisper for all available models.

    Returns:
        List of tuples: [(segment_text, (start_sec, end_sec)), ...]
    """
    if not os.path.exists(audio_path):
        return f"Error: Audio file not found at '{audio_path}'."

    try:
        
        # Load a Whisper model. The first time this is run, it will download the model.
        # Model options: "tiny", "base", "small", "medium", "large"
        # Using faster-whisper. It's recommended to use "base" for a good balance of speed and accuracy.

        logging.debug(f"Loading model ('{model_name}')...")
        # Run on CPU with INT8
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        logging.debug("Model loaded successfully.")

        logging.debug(f"Starting transcription for '{audio_path}'...")
        segments, info = model.transcribe(audio_path, beam_size=5)
        logging.debug(f"Detected language '{info.language}' with probability {info.language_probability}")
        logging.debug("Transcription complete.")

        # The 'segments' is an iterator of Segment objects.
        tuples: List[Tuple[str, Tuple[float, float]]] = [
            (seg.text.strip(), (seg.start, seg.end))
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
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="The Whisper model to use for transcription (default: base)."
    )
    
    args = parser.parse_args()

    # Call to the the transcription function
    text = transcribe_audio(args.audio_file, args.model)

    # Print the result
    print("\n--- Transcription Result ---")
    if isinstance(text, list):
        for segment in text:
            print(segment)
    else:
        print(text) # Print error message
    print("--------------------------")
