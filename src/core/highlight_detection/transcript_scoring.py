from tqdm import tqdm

def txt_score_per_shot(shots, spans, transcribed_segments=None):
    """
    Convert LLM spans → per-shot TXT coverage scores.
    
    Enhanced version that also considers sentence completeness.
    
    Args:
        shots: List of shot boundaries
        spans: LLM-selected time spans
        transcribed_segments: Optional - full transcript for coherence checking
    """
    def overlap_ratio(s0, e0):
        overlap = 0.0
        for s, e in spans:
            overlap += max(0.0, min(e0, e) - max(s0, s))
        return overlap / max(e0 - s0, 1e-6)
    
    def coherence_score(shot_start, shot_end, segments):
        """
        Score how well the shot aligns with sentence boundaries.
        Returns 1.0 if perfect alignment, lower if cuts mid-sentence.
        """
        if segments is None:
            return 1.0  # No penalty if we don't have segment info
        
        score = 1.0
        
        # Find text that starts/ends in this shot
        for text, (t_start, t_end) in segments:
            # Check if shot cuts into the middle of this text segment
            if t_start < shot_start < t_end:
                # Shot starts mid-segment
                if not any(text[:20].strip().startswith(w) for w in ['.', '!', '?']):
                    score -= 0.2  # Penalty for starting mid-sentence
                    
            if t_start < shot_end < t_end:
                # Shot ends mid-segment
                if not text.strip().endswith(('.', '!', '?')):
                    score -= 0.3  # Bigger penalty for ending mid-sentence
        
        return max(score, 0.3)  # Minimum score of 0.3

    out = []
    for sh in tqdm(shots, desc="Calculating TXT branch scores"):
        s, e = sh["start"], sh["end"]
        base_score = overlap_ratio(s, e)
        
        # Apply coherence modifier
        coherence = coherence_score(s, e, transcribed_segments)
        final_score = base_score * coherence
        
        out.append({
            "shot_id": sh["shot_id"],
            "start": s, 
            "end": e,
            "TXT": final_score,
            "TXT_base": base_score,
            "coherence": coherence
        })
    return out