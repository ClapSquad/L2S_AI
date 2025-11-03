import json, pathlib, numpy as np, torch, open_clip, cv2, librosa, subprocess
from PIL import Image

def motion_score(video_path, start, end, step=0.25):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, start*1000)
    ret, prev = cap.read()
    if not ret:
        print(f"[motion_score] Failed to read frame at {start}s")
        return 0.0
    prev = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    vals = []
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t*1000)
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        vals.append(float(np.mean(cv2.absdiff(prev, gray))))
        prev = gray
        t += step
    cap.release()
    return float(np.mean(vals)) if vals else 0.0

def loudness(video_path, start, end):
    import tempfile, os, subprocess, librosa

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    # run ffmpeg and capture errors
    result = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", video_path,
        "-ac", "1", "-ar", "16000",
        tmp_path
    ], capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(tmp_path):
        print("[FFmpeg Error]", result.stderr)
        return 0.0

    try:
        y, sr = librosa.load(tmp_path, sr=None)
        rms = float(librosa.feature.rms(y=y).mean())
    except Exception as e:
        print("[Librosa Error]", e)
        rms = 0.0
    finally:
        os.remove(tmp_path)

    return rms

def compute_hd_branch(video_path, shots, title, summary, cfg):
    model, _, preprocess = open_clip.create_model_and_transforms(cfg["clip_model"], pretrained="laion2b_s34b_b79k")
    tokenizer = open_clip.get_tokenizer(cfg["clip_model"])
    model.eval().to("cuda" if torch.cuda.is_available() else "cpu")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    prompts = cfg["generic_prompts"]
    txts = tokenizer(prompts).to(device)
    with torch.no_grad():
        txt_feats = model.encode_text(txts)
        txt_feats /= txt_feats.norm(dim=-1, keepdim=True)

    out = []
    for sh in shots:
        s,e = sh["start"], sh["end"]
        motion = motion_score(video_path, s, e)
        loud = loudness(video_path, s, e)

        # speech rate (needs whisper words)
        sr_path = pathlib.Path("data/asr")/f"{pathlib.Path(video_path).stem}.words.json"
        if sr_path.exists():
            words = json.load(open(sr_path))["words"]
            count = sum(1 for w in words if w["start"]>=s and w["end"]<=e)
            dur = e-s if e>s else 1
            speech = count/dur
        else:
            speech = 0.0

        # CLIP similarity with generic prompts
        kf_dir = pathlib.Path("data/keyframes")/pathlib.Path(video_path).stem/f"shot_{sh['shot_id']:04d}"
        sims=[]
        for img_file in kf_dir.glob("*.jpg"):
            img = preprocess(Image.open(img_file).convert("RGB")).unsqueeze(0).to(device)
            with torch.no_grad():
                img_feat = model.encode_image(img)
                img_feat /= img_feat.norm(dim=-1, keepdim=True)
                sim = (img_feat @ txt_feats.T).max().item()
            sims.append(sim)
        clip_score = max(sims) if sims else 0.0
        out.append({"shot_id":sh["shot_id"],"start":s,"end":e,
                    "motion":motion,"clip":clip_score,"loud":loud,"speech":speech})

    # normalize + combine
    for k in ["motion","clip","loud","speech"]:
        vals = [r[k] for r in out]
        lo,hi = min(vals),max(vals)
        for r in out:
            r[k] = 0 if hi==lo else (r[k]-lo)/(hi-lo)
    for r in out:
        r["HD"] = (cfg["weights"]["motion"]*r["motion"] +
                   cfg["weights"]["clip"]*r["clip"] +
                   cfg["weights"]["loud"]*r["loud"] +
                   cfg["weights"]["speech"]*r["speech"])
    return out
