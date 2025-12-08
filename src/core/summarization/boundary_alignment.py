"""
Sentence Boundary Alignment Module

This module adjusts video cut timestamps to align with natural speech boundaries
(sentence endings, pauses) to prevent mid-sentence cuts.

Think of it like this:
- Original timestamp: Cuts at 5.3 seconds (mid-sentence)
- Adjusted timestamp: Moves to 5.8 seconds (end of sentence)
"""

import re
from typing import List, Tuple


def find_sentence_boundaries(transcribed_segments: List[Tuple[str, Tuple[float, float]]]) -> List[dict]:
    """
    Analyze transcript to find where sentences start and end.
    
    Args:
        transcribed_segments: List of (text, (start_time, end_time)) from Whisper
        
    Returns:
        List of sentence boundary markers with timestamps
        
    Example:
        Input: [("Hello world.", (0.0, 1.5)), ("How are you?", (1.5, 3.0))]
        Output: [
            {"type": "end", "time": 1.5, "text": "Hello world."},
            {"type": "end", "time": 3.0, "text": "How are you?"}
        ]
    """
    boundaries = []
    
    # Sentence-ending patterns (period, question mark, exclamation)
    sentence_end_pattern = r'[.!?](?:\s|$)'
    
    # Mid-thought indicators (words that suggest continuation)
    continuation_words = ['and', 'but', 'so', 'because', 'which', 'that', 'however', 
                         'therefore', 'also', 'then', 'or', 'nor', 'yet']
    
    for text, (start, end) in transcribed_segments:
        text_clean = text.strip()
        
        # Check if this segment ends with a sentence-ending punctuation
        if re.search(sentence_end_pattern, text_clean):
            boundaries.append({
                "type": "sentence_end",
                "time": end,
                "text": text_clean,
                "is_complete": True
            })
        else:
            boundaries.append({
                "type": "incomplete",
                "time": end,
                "text": text_clean,
                "is_complete": False
            })
        
        # Check if segment starts with a continuation word (mid-thought start)
        first_word = text_clean.split()[0].lower() if text_clean.split() else ""
        if first_word in continuation_words:
            boundaries[-1]["starts_mid_thought"] = True
    
    return boundaries


def find_nearest_sentence_end(target_time: float, 
                               boundaries: List[dict], 
                               direction: str = "forward",
                               max_shift: float = 3.0) -> float:
    """
    Find the nearest sentence ending to a given timestamp.
    
    Args:
        target_time: The timestamp we want to adjust
        boundaries: List of sentence boundaries from find_sentence_boundaries()
        direction: "forward" to look ahead, "backward" to look behind, "nearest" for closest
        max_shift: Maximum seconds we're willing to shift the timestamp
        
    Returns:
        Adjusted timestamp that aligns with a sentence boundary
        
    Example:
        target_time = 5.3 (mid-sentence)
        If sentence ends at 5.8, returns 5.8
        If no good boundary found within max_shift, returns original 5.3
    """
    sentence_ends = [b for b in boundaries if b["is_complete"]]
    
    if not sentence_ends:
        return target_time
    
    candidates = []
    
    for boundary in sentence_ends:
        diff = boundary["time"] - target_time
        
        if direction == "forward" and 0 <= diff <= max_shift:
            candidates.append((diff, boundary["time"]))
        elif direction == "backward" and -max_shift <= diff <= 0:
            candidates.append((abs(diff), boundary["time"]))
        elif direction == "nearest" and abs(diff) <= max_shift:
            candidates.append((abs(diff), boundary["time"]))
    
    if candidates:
        # Return the closest valid boundary
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    return target_time


def align_timestamps_to_sentences(
    timestamps: List[List[float]], 
    transcribed_segments: List[Tuple[str, Tuple[float, float]]],
    max_extension: float = 2.0,
    max_trim: float = 1.0
) -> List[List[float]]:
    """
    Main function: Adjust all timestamps to align with sentence boundaries.
    
    This is the function you'll call from video_to_summarization.py
    
    Args:
        timestamps: List of [start, end] pairs from LLM
        transcribed_segments: Original transcript with timing
        max_extension: How much we can extend a clip to complete a sentence
        max_trim: How much we can trim from the start to avoid mid-sentence starts
        
    Returns:
        Adjusted timestamps that respect sentence boundaries
        
    Example:
        Input:  [[0.0, 5.3], [10.0, 15.2]]  # Might cut mid-sentence
        Output: [[0.0, 5.8], [9.5, 15.8]]   # Aligned to sentence boundaries
    """
    boundaries = find_sentence_boundaries(transcribed_segments)
    adjusted = []
    
    for start, end in timestamps:
        # Adjust END time: extend forward to complete the sentence
        new_end = find_nearest_sentence_end(end, boundaries, direction="forward", max_shift=max_extension)
        
        # Adjust START time: if we're starting mid-sentence, try to include sentence start
        # or trim to next sentence start
        new_start = start
        
        # Check if we're starting mid-thought
        for boundary in boundaries:
            if boundary["time"] <= start and boundary.get("starts_mid_thought"):
                # We might be cutting into a continuation - try to find previous sentence end
                prev_end = find_nearest_sentence_end(start, boundaries, direction="backward", max_shift=max_trim)
                if prev_end < start:
                    new_start = prev_end
                break
        
        # Ensure we don't create invalid ranges
        if new_start < new_end:
            adjusted.append([new_start, new_end])
        else:
            adjusted.append([start, end])  # Fall back to original
    
    return adjusted


def check_segment_coherence(text: str) -> dict:
    """
    Analyze a text segment for coherence issues.
    
    Useful for debugging and quality checks.
    
    Args:
        text: The text content of a segment
        
    Returns:
        Dict with coherence analysis results
    """
    issues = []
    
    # Check for incomplete ending
    incomplete_endings = ['...', '—', '-', ',', 'and', 'but', 'so', 'because', 'which']
    text_clean = text.strip()
    
    for ending in incomplete_endings:
        if text_clean.endswith(ending) or text_clean.lower().endswith(ending):
            issues.append(f"Segment ends with incomplete marker: '{ending}'")
    
    # Check for mid-thought start
    continuation_starters = ['and ', 'but ', 'so ', 'because ', 'which ', 'that ', 
                            'however ', 'therefore ', 'also ', 'then ']
    text_lower = text_clean.lower()
    for starter in continuation_starters:
        if text_lower.startswith(starter):
            issues.append(f"Segment starts with continuation word: '{starter.strip()}'")
    
    # Check minimum word count
    word_count = len(text_clean.split())
    if word_count < 5:
        issues.append(f"Segment too short ({word_count} words)")
    
    return {
        "text": text_clean,
        "word_count": word_count,
        "is_coherent": len(issues) == 0,
        "issues": issues
    }