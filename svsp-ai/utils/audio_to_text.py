# to run this first you need to install whisper (also whisper requires ffmpeg)
# pip install openai-whisper
# sudo apt update && sudo apt install ffmpeg

# To use this script
# python audio_to_text.py example_file.mp3

import whisper
import argparse
import logging, os

def transcribe_audio(audio_path: str, model_name: str = "base") -> str:
    """
    Transcribes an audio file to text using OpenAI's Whisper.

    Args:
        audio_path: The path to the audio file (e.g., .mp3, .wav, .m4a).
        model_name: The name of the Whisper model to use 
                    (e.g., "tiny", "base", "small", "medium", "large").
                    It defaults to base.

    Returns:
        The transcribed text as a string, or an error message if transcription fails.
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
        logging.debug(f"Detected language: {language}")
        logging.debug("Transcription complete.")

        transcribed_text = result["text"]
        return transcribed_text

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
    print(text)
    print("--------------------------")
