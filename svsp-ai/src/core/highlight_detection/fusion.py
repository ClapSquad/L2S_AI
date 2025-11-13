import json, pathlib

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
