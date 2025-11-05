# utils/highlight_detection/txt_branch.py
import os, json

def compute_txt_branch(video_path):
    """
    Re-use the existing Gemini summarizer as the TXT branch.
    Returns: list of [start, end] spans.
    """
    filename = os.path.basename(video_path)
    video_id = os.path.splitext(filename)[0]

    timestamps = None
    with open(r"summarized_results.jsonl", "r") as f:
        for line in f:
            data = json.loads(line)
            if data.get("id") == video_id:
                timestamps = data["result"]["timestamps"]
                break

    return timestamps

def txt_score_per_shot(shots, spans):
    """Convert LLM spans → per-shot TXT coverage scores."""
    def overlap_ratio(s0, e0):
        overlap = 0.0
        for s, e in spans:
            overlap += max(0.0, min(e0, e) - max(s0, s))
        return overlap / max(e0 - s0, 1e-6)

    out = []
    for sh in shots:
        s, e = sh["start"], sh["end"]
        out.append({
            "shot_id": sh["shot_id"],
            "start": s, "end": e,
            "TXT": overlap_ratio(s, e)
        })
    return out
