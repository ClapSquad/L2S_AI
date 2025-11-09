import json, pathlib, numpy as np, torch, open_clip, cv2
from tqdm import tqdm
from PIL import Image

# Compute motion score for a video segment
def motion_score(video_path, start, end, step=0.25):
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, start*1000) # set start time
    ret, prev = cap.read() # read first frame
    if not ret:
        print(f"[motion_score] Failed to read frame at {start}s")
        return 0.0
    
    prev = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY) # convert video to grayscale
    vals = []
    t = start

    # iterate through frames at given step intervals
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t*1000)
        ret, frame = cap.read() # read next frame
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        vals.append(float(np.mean(cv2.absdiff(prev, gray)))) # compute difference between frames
        prev = gray
        t += step
    cap.release() # release video capture object

    return float(np.mean(vals)) if vals else 0.0 # return average motion score

# Compute loudness score for a video segment
def loudness(video_path, start, end):
    import tempfile, os, subprocess, librosa
    # librosa is a library for audio analysis

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp: # temp file to store audio segment
        tmp_path = tmp.name 

    # run ffmpeg 
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
        y, sr = librosa.load(tmp_path, sr=None) # load audio file
        rms = float(librosa.feature.rms(y=y).mean()) # compute RMS loudness
    except Exception as e:
        print("[Librosa Error]", e)
        rms = 0.0
    finally:
        os.remove(tmp_path)

    return rms

# Compute highlight detection (HD) branch scores
def compute_hd_branch(video_path, shots, title, summary, cfg):
    # create CLIP model and preprocessing function
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
    with tqdm(shots, desc="Computing HD branch scores") as pbar:
        for sh in pbar:
            s, e = sh["start"], sh["end"]  # shot start/end times

            pbar.set_description(f"Shot {sh['shot_id']}: Motion")
            motion = motion_score(video_path, s, e)

            pbar.set_description(f"Shot {sh['shot_id']}: Loudness")
            loud = loudness(video_path, s, e)

            # speech rate (uses whisper words)
            pbar.set_description(f"Shot {sh['shot_id']}: Speech Rate")
            sr_path = pathlib.Path("data/asr") / f"{pathlib.Path(video_path).stem}.words.json"
            if sr_path.exists():
                words = json.load(open(sr_path))["words"]
                count = sum(1 for w in words if w["start"] >= s and w["end"] <= e)
                dur = e - s if e > s else 1
                speech = count / dur
            else:
                speech = 0.0

            # CLIP similarity with generic prompts
            if cfg["weights"]["clip"] <= 0.0:
                clip_score = 0.0
            else:
                pbar.set_description(f"Shot {sh['shot_id']}: CLIP Similarity")
                kf_dir = pathlib.Path("data/keyframes") / pathlib.Path(video_path).stem / f"shot_{sh['shot_id']:04d}"
                sims = []
                for img_file in kf_dir.glob("*.jpg"):
                    img = preprocess(Image.open(img_file).convert("RGB")).unsqueeze(0).to(device)
                    with torch.no_grad():
                        img_feat = model.encode_image(img)
                        img_feat /= img_feat.norm(dim=-1, keepdim=True)
                        sim = (img_feat @ txt_feats.T).max().item()
                    sims.append(sim)
                clip_score = max(sims) if sims else 0.0
                out.append({"shot_id": sh["shot_id"], "start": s, "end": e,
                            "motion": motion, "clip": clip_score, "loud": loud, "speech": speech})

    # normalize + combine
    print("Calculating final HD scores ...")
    for k in ["motion","clip","loud","speech"]:
        vals = [r[k] for r in out]
        lo,hi = min(vals),max(vals)
        for r in out:
            r[k] = 0 if hi==lo else (r[k]-lo)/(hi-lo)
    for r in out:
        # (weight_1 * motion + weight_2 * clip + weight_3 * loud + weight_4 * speech)
        r["HD"] = (cfg["weights"]["motion"]*r["motion"] +
                   cfg["weights"]["clip"]*r["clip"] +
                   cfg["weights"]["loud"]*r["loud"] +
                   cfg["weights"]["speech"]*r["speech"])
    return out