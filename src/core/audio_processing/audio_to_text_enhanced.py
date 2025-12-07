"""
Enhanced Audio Transcription with Word-Level Timestamps

This module extends the basic Whisper transcription to support:
1. Word-level timestamps (for karaoke-style subtitles)
2. Segment-level timestamps (for traditional subtitles)
3. Language detection
4. Multiple output formats

Think of this like a super-powered transcription tool:
- Basic mode: "Here's what was said and when the sentence started/ended"
- Word mode: "Here's each individual word and exactly when it was spoken"

Usage:
    # For karaoke-style (word-by-word highlighting)
    result = transcribe_audio_enhanced("video.mp3", word_timestamps=True)
    
    # For traditional subtitles (sentence-by-sentence)
    result = transcribe_audio_enhanced("video.mp3", word_timestamps=False)
"""

import argparse
import logging
import os
from typing import List, Dict, Tuple, Union, Optional
from dataclasses import dataclass
from faster_whisper import WhisperModel


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class WordInfo:
    """
    Represents a single word with its timing information.
    
    Think of this like a flashcard:
    - The word itself ("Hello")
    - When to show it (start time: 0.5 seconds)
    - When to hide it (end time: 0.8 seconds)
    - How confident we are it's correct (probability: 0.95 = 95% sure)
    """
    word: str
    start: float  # Start time in seconds
    end: float    # End time in seconds
    probability: float  # Confidence score (0.0 to 1.0)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "word": self.word,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "probability": round(self.probability, 3)
        }


@dataclass
class SegmentInfo:
    """
    Represents a sentence/segment with optional word-level details.
    
    Think of this like a paragraph container:
    - The full text of the sentence
    - When the sentence starts and ends
    - Optionally, the breakdown of each word
    """
    text: str
    start: float
    end: float
    words: Optional[List[WordInfo]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
        }
        if self.words:
            result["words"] = [w.to_dict() for w in self.words]
        return result


@dataclass
class TranscriptionResult:
    """
    The complete transcription output.
    
    Contains:
    - All segments (sentences) with their timing
    - Detected language information
    - Configuration used for transcription
    """
    segments: List[SegmentInfo]
    language: str
    language_probability: float
    has_word_timestamps: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "language": self.language,
            "language_probability": round(self.language_probability, 3),
            "has_word_timestamps": self.has_word_timestamps,
            "segments": [s.to_dict() for s in self.segments]
        }
    
    def get_all_words(self) -> List[WordInfo]:
        """
        Get a flat list of all words from all segments.
        Useful for generating karaoke subtitles.
        """
        if not self.has_word_timestamps:
            raise ValueError("Word timestamps not available. Re-transcribe with word_timestamps=True")
        
        all_words = []
        for segment in self.segments:
            if segment.words:
                all_words.extend(segment.words)
        return all_words
    
    def to_legacy_format(self) -> List[Tuple[str, Tuple[float, float]]]:
        """
        Convert to the original format for backward compatibility.
        Returns: [(text, (start, end)), ...]
        """
        return [(seg.text, (seg.start, seg.end)) for seg in self.segments]


# ============================================================================
# MAIN TRANSCRIPTION FUNCTION
# ============================================================================

def transcribe_audio_enhanced(
    audio_path: str,
    model_name: str = "base",
    word_timestamps: bool = True,
    language: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8"
) -> Union[TranscriptionResult, str]:
    """
    Transcribe an audio file with optional word-level timestamps.
    
    This is the main function you'll use. It's like asking someone to:
    1. Listen to an audio file
    2. Write down everything that was said
    3. Note exactly when each word (or sentence) was spoken
    
    Args:
        audio_path: Path to the audio file (.mp3, .wav, .m4a, etc.)
        model_name: Which Whisper model to use:
            - "tiny": Fastest, least accurate (good for testing)
            - "base": Good balance of speed and accuracy (recommended)
            - "small": Better accuracy, slower
            - "medium": Even better accuracy, even slower
            - "large": Best accuracy, slowest (needs GPU)
        word_timestamps: If True, get timing for each word (for karaoke effect)
                        If False, only get timing for sentences (simpler)
        language: Force a specific language (e.g., "en", "ko", "ja")
                 If None, Whisper will auto-detect the language
        device: "cpu" or "cuda" (GPU). Use "cuda" if you have a good GPU
        compute_type: "int8" (faster, less memory) or "float16" (more accurate, needs GPU)
    
    Returns:
        TranscriptionResult object with all the data, or error string if failed
    
    Example:
        # Basic usage with word timestamps
        result = transcribe_audio_enhanced("speech.mp3", word_timestamps=True)
        
        # Get all words for karaoke subtitles
        for word in result.get_all_words():
            print(f"{word.word} appears at {word.start}s - {word.end}s")
    """
    
    # Step 1: Check if file exists
    if not os.path.exists(audio_path):
        return f"Error: Audio file not found at '{audio_path}'."
    
    try:
        # Step 2: Load the Whisper model
        # This is like hiring a translator - first time takes longer as we download the model
        logging.info(f"Loading Whisper model ('{model_name}')...")
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        logging.info("Model loaded successfully.")
        
        # Step 3: Prepare transcription options
        transcribe_options = {
            "beam_size": 5,  # Higher = more accurate but slower
            "word_timestamps": word_timestamps,  # This is the key setting for karaoke!
        }
        
        # Add language if specified
        if language:
            transcribe_options["language"] = language
        
        # Step 4: Run transcription
        logging.info(f"Starting transcription for '{audio_path}'...")
        logging.info(f"Word timestamps: {'enabled for karaoke style' if word_timestamps else 'disabled (sentence-level only)'}")
        
        segments_iterator, info = model.transcribe(audio_path, **transcribe_options)
        
        logging.info(f"Detected language: '{info.language}' (confidence: {info.language_probability:.1%})")
        
        # Step 5: Process each segment
        segments = []
        
        for seg in segments_iterator:
            # Create word information if word timestamps are enabled
            words = None
            if word_timestamps and hasattr(seg, 'words') and seg.words:
                words = [
                    WordInfo(
                        word=w.word.strip(),
                        start=w.start,
                        end=w.end,
                        probability=w.probability if hasattr(w, 'probability') else 1.0
                    )
                    for w in seg.words
                    if w.word.strip()  # Skip empty words
                ]
            
            segment_info = SegmentInfo(
                text=seg.text.strip(),
                start=seg.start,
                end=seg.end,
                words=words
            )
            segments.append(segment_info)
        
        logging.info(f"Transcription complete. Found {len(segments)} segments.")
        
        # Step 6: Return the result
        return TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            has_word_timestamps=word_timestamps
        )
          
    except Exception as e:
        logging.error(f"Transcription error: {e}")
        return f"An error occurred during transcription: {e}"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def transcribe_for_karaoke(
    audio_path: str,
    model_name: str = "base"
) -> Union[List[Dict], str]:
    """
    Convenience function specifically for karaoke-style subtitles.
    
    Returns a simple list of word dictionaries, perfect for subtitle generation.
    
    Example output:
    [
        {"word": "Hello", "start": 0.0, "end": 0.4},
        {"word": "world", "start": 0.5, "end": 0.9},
        ...
    ]
    """
    result = transcribe_audio_enhanced(
        audio_path,
        model_name=model_name,
        word_timestamps=True
    )
    
    if isinstance(result, str):  # Error occurred
        return result
    
    return [word.to_dict() for word in result.get_all_words()]


def transcribe_for_simple_subtitles(
    audio_path: str,
    model_name: str = "base"
) -> Union[List[Tuple[str, Tuple[float, float]]], str]:
    """
    Convenience function for traditional sentence-level subtitles.
    
    Returns the legacy format: [(text, (start, end)), ...]
    
    This maintains backward compatibility with your existing code.
    """
    result = transcribe_audio_enhanced(
        audio_path,
        model_name=model_name,
        word_timestamps=False
    )
    
    if isinstance(result, str):  # Error occurred
        return result
    
    return result.to_legacy_format()


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Transcribe audio with optional word-level timestamps for karaoke-style subtitles."
    )
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to the audio file to transcribe"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper model to use (default: base)"
    )
    parser.add_argument(
        "--words",
        action="store_true",
        default=True,
        help="Enable word-level timestamps (default: True)"
    )
    parser.add_argument(
        "--no-words",
        action="store_true",
        help="Disable word-level timestamps (sentence-level only)"
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Force specific language (e.g., 'en', 'ko'). Auto-detect if not specified."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (optional)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # Determine if word timestamps should be enabled
    word_timestamps = not args.no_words
    
    # Run transcription
    result = transcribe_audio_enhanced(
        args.audio_file,
        model_name=args.model,
        word_timestamps=word_timestamps,
        language=args.language
    )
    
    # Output results
    if isinstance(result, str):
        logging.error(result)
    else:
        logging.info("\n" + "="*60)
        logging.info("TRANSCRIPTION RESULT")
        logging.info("="*60)
        logging.info(f"Language: {result.language} ({result.language_probability:.1%} confidence)")
        logging.info(f"Word timestamps: {'Yes' if result.has_word_timestamps else 'No'}")
        logging.info(f"Total segments: {len(result.segments)}")
        
        if result.has_word_timestamps:
            total_words = sum(len(seg.words or []) for seg in result.segments)
            logging.info(f"Total words: {total_words}")
        
        logging.info("\n--- Segments ---")
        for i, seg in enumerate(result.segments[:5], 1):  # Show first 5 segments
            logging.info(f"\n[{i}] {seg.start:.2f}s - {seg.end:.2f}s")
            logging.info(f"    Text: {seg.text}")
            if seg.words:
                words_preview = ", ".join(f'"{w.word}"' for w in seg.words[:5])
                if len(seg.words) > 5:
                    words_preview += f"... (+{len(seg.words)-5} more)"
                logging.info(f"    Words: {words_preview}")
        
        if len(result.segments) > 5:
            logging.info(f"\n... and {len(result.segments) - 5} more segments")
        
        # Save to file if requested
        if args.output:
            import json
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            logging.info(f"\nSaved to: {args.output}")