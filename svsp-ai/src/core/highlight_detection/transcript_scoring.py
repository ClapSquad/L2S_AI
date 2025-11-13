from tqdm import tqdm

def txt_score_per_shot(shots, spans):
    """Convert LLM spans → per-shot TXT coverage scores."""
    def overlap_ratio(s0, e0):
        overlap = 0.0
        for s, e in spans:
            overlap += max(0.0, min(e0, e) - max(s0, s))
        return overlap / max(e0 - s0, 1e-6)

    out = []
    for sh in tqdm(shots, desc="Calculating TXT branch scores"):
        s, e = sh["start"], sh["end"]
        out.append({
            "shot_id": sh["shot_id"],
            "start": s, "end": e,
            "TXT": overlap_ratio(s, e)
        })
    return out
