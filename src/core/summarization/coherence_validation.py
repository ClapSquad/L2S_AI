"""
Coherence Validation Module

This module performs a final check to ensure selected segments
form a coherent narrative when played together.

Think of it as a "proofreader" for your video summary.
"""

from typing import List, Tuple
from .llm_client import call_gemini
import logging


def validate_narrative_coherence(
    selected_segments: List[Tuple[str, Tuple[float, float]]],
    all_segments: List[Tuple[str, Tuple[float, float]]]
) -> dict:
    """
    Check if selected segments form a coherent narrative.
    
    Args:
        selected_segments: The segments chosen for the summary
        all_segments: All available transcript segments
        
    Returns:
        Dict with validation results and suggested fixes
    """
    
    # Combine selected segment texts
    combined_text = " ".join([text for text, _ in selected_segments])
    
    validation_prompt = f"""
    You are a video editor reviewing a summary. Check if these transcript segments 
    make sense when played back-to-back.

    SELECTED SEGMENTS (in order):
    {chr(10).join([f'{i+1}. "{text}" ({start:.1f}s - {end:.1f}s)' 
                   for i, (text, (start, end)) in enumerate(selected_segments)])}

    COMBINED TEXT (what viewer will hear):
    "{combined_text}"

    EVALUATE:
    1. Does each segment start at a natural beginning (not mid-sentence)?
    2. Does each segment end at a natural stopping point?
    3. Do the segments flow logically from one to the next?
    4. Would a viewer understand this without the full video context?

    OUTPUT FORMAT (JSON only):
    {{
        "is_coherent": true/false,
        "overall_score": 1-10,
        "issues": [
            {{
                "segment_index": 1,
                "issue": "Starts mid-sentence with 'and'",
                "suggestion": "Include previous sentence for context"
            }}
        ],
        "flow_analysis": "Brief description of how well segments connect"
    }}
    """
    
    result = call_gemini("gemini-2.5-flash", validation_prompt, as_json=True)
    return result.get('json', {"is_coherent": True, "issues": []})


def fix_coherence_issues(
    timestamps: List[List[float]],
    transcribed_segments: List[Tuple[str, Tuple[float, float]]],
    validation_result: dict
) -> List[List[float]]:
    """
    Attempt to fix identified coherence issues by adjusting timestamps.
    
    Args:
        timestamps: Original [start, end] pairs
        transcribed_segments: Full transcript
        validation_result: Output from validate_narrative_coherence
        
    Returns:
        Adjusted timestamps
    """
    if validation_result.get("is_coherent", True):
        return timestamps
    
    adjusted = timestamps.copy()
    
    for issue in validation_result.get("issues", []):
        idx = issue.get("segment_index", 0) - 1  # Convert to 0-indexed
        if idx < 0 or idx >= len(adjusted):
            continue
            
        issue_type = issue.get("issue", "").lower()
        
        # Handle common issues
        if "mid-sentence" in issue_type or "starts with" in issue_type:
            # Try to extend backward to previous segment
            if idx > 0:
                # Merge with previous segment
                adjusted[idx][0] = adjusted[idx-1][0]
                adjusted[idx-1] = None  # Mark for removal
                
        elif "incomplete" in issue_type or "ends with" in issue_type:
            # Try to extend forward
            current_end = adjusted[idx][1]
            # Find next segment that completes the thought
            for text, (start, end) in transcribed_segments:
                if start >= current_end and end <= current_end + 5:  # Within 5 seconds
                    if text.strip().endswith(('.', '!', '?')):
                        adjusted[idx][1] = end
                        break
    
    # Remove None entries and clean up
    adjusted = [ts for ts in adjusted if ts is not None]
    
    return adjusted


def iterative_coherence_improvement(
    timestamps: List[List[float]],
    transcribed_segments: List[Tuple[str, Tuple[float, float]]],
    max_iterations: int = 2
) -> List[List[float]]:
    """
    Iteratively improve coherence until satisfied or max iterations reached.
    
    This is the main function you'll call from your pipeline.
    
    Args:
        timestamps: Initial timestamps from LLM
        transcribed_segments: Full transcript
        max_iterations: Maximum improvement attempts
        
    Returns:
        Improved timestamps
    """
    current_timestamps = timestamps
    
    for iteration in range(max_iterations):
        # Get the text for selected segments
        selected = []
        for start, end in current_timestamps:
            segment_text = " ".join([
                text for text, (s, e) in transcribed_segments
                if s >= start - 0.1 and e <= end + 0.1
            ])
            selected.append((segment_text, (start, end)))
        
        # Validate coherence
        validation = validate_narrative_coherence(selected, transcribed_segments)
        
        if validation.get("is_coherent", True):
            logging.info(f"Coherence achieved after {iteration + 1} iteration(s)")
            break
            
        logging.info(f"Iteration {iteration + 1}: Found {len(validation.get('issues', []))} issues")
        
        # Try to fix issues
        current_timestamps = fix_coherence_issues(
            current_timestamps, 
            transcribed_segments, 
            validation
        )
    
    return current_timestamps