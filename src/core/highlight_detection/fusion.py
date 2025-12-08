import json, pathlib

def adjust_shots_to_speech(shots: list, transcribed_segments: list) -> list:
    """
    Adjust shot boundaries to align with speech patterns.
    
    The idea: If a shot cuts mid-sentence, extend it to the sentence end.
    
    Args:
        shots: List of {"shot_id": int, "start": float, "end": float}
        transcribed_segments: List of (text, (start, end)) from Whisper
        
    Returns:
        Adjusted shots with speech-aligned boundaries
    """
    adjusted_shots = []
    
    for shot in shots:
        shot_start = shot["start"]
        shot_end = shot["end"]
        
        # Find transcript segments that overlap with this shot
        overlapping_text = []
        for text, (t_start, t_end) in transcribed_segments:
            # Check if transcript segment overlaps with shot
            if t_start < shot_end and t_end > shot_start:
                overlapping_text.append({
                    "text": text,
                    "start": t_start,
                    "end": t_end
                })
        
        if not overlapping_text:
            adjusted_shots.append(shot)
            continue
        
        # Check if the last overlapping segment is incomplete
        last_segment = overlapping_text[-1]
        if not last_segment["text"].strip().endswith(('.', '!', '?', '"')):
            # The shot cuts mid-sentence!
            # Find the next segment that completes the sentence
            for text, (t_start, t_end) in transcribed_segments:
                if t_start >= last_segment["end"]:
                    # This is the next segment
                    if text.strip().endswith(('.', '!', '?', '"')):
                        # Extend shot to include this sentence completion
                        shot_end = min(t_end, shot_end + 3.0)  # Max 3s extension
                    break
        
        adjusted_shots.append({
            "shot_id": shot["shot_id"],
            "start": shot_start,
            "end": shot_end,
            "speech_adjusted": True
        })
    
    return adjusted_shots

def fuse_and_select(video_path, hd_json, txt_json, w_hd, w_txt, w_aud,
                    keep_seconds, min_len, max_len, merge_gap):
    hd = json.load(open(hd_json)) # load HD branch scores
    txt = json.load(open(txt_json)) # load TXT branch scores
    by_id = {r["shot_id"]: r for r in hd}
    for t in txt:
        by_id[t["shot_id"]]["TXT"] = t["TXT"]

    # audio energy
    # for r in by_id.values():
    #     r["AUD"] = 0.6*r["loud"] + 0.4*r["speech"]

    # normalize
    for key in ["HD","TXT","AUD"]:
        vals=[r.get(key,0.0) for r in by_id.values()]
        lo,hi=min(vals),max(vals)
        for r in by_id.values():
            r[key]=0 if hi==lo else (r[key]-lo)/(hi-lo)

    for r in by_id.values():
        # r["final"]=w_hd*r["HD"]+w_txt*r.get("TXT",0)+w_aud*r["AUD"]
        r["final"]=w_hd*r["HD"]+w_txt*r.get("TXT",0)

    ranked=sorted(by_id.values(),key=lambda x:x["final"],reverse=True)
    picked,acc=[],0
    for i, r in enumerate(ranked):
        dur=r["end"]-r["start"]
        if acc+dur<=keep_seconds:
            picked.append({"start":r["start"],"end":r["end"],"score":r["final"], "rank": i + 1})
            acc+=dur

    # merge & clamp
    picked.sort(key=lambda x:x["start"])
    merged=[]
    for s in picked:
        if not merged or s["start"] - merged[-1]["end"] > merge_gap:
            merged.append(s)
        else:
            # When merging, keep the rank of the segment with the better score (lower rank number)
            if s["rank"] < merged[-1]["rank"]:
                merged[-1]["rank"] = s["rank"]
            merged[-1]["end"] = max(merged[-1]["end"], s["end"])
    final=[]
    for s in merged:
        dur=s["end"]-s["start"]
        if dur<min_len: continue
        if dur>max_len: s["end"]=s["start"]+max_len
        final.append(s)
    out_path=pathlib.Path("data/shots")/f"{pathlib.Path(video_path).stem}.highlights.json"
    json.dump(final,open(out_path,"w"),indent=2)
    return [[s["start"], s["end"], s["score"], s["rank"]] for s in final]
