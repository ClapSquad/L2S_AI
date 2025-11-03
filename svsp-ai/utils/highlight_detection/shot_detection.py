import os, json, subprocess, pathlib, cv2

def detect_shots(video_path, init_threshold=27, min_threshold=5, target_min_scenes=5):
    """Detect shots using PySceneDetect (content detector)."""
    stem = pathlib.Path(video_path).stem
    out_dir = pathlib.Path("data/shots")
    out_dir.mkdir(parents=True, exist_ok=True)

    threshold = init_threshold
    shots = []

    # Clean up previous CSV output to prevent scenedetect from appending
    for old_csv in out_dir.glob(f"{stem}-Scenes.csv"):
        old_csv.unlink()

    while threshold >= min_threshold:
        # Run PySceneDetect
        subprocess.run([
            "scenedetect", "--input", video_path,
            "detect-content", "--threshold", str(threshold),
            "list-scenes", "--output", str(out_dir)
        ], check=True)

        csv_path = next(out_dir.glob(f"{stem}-Scenes.csv"), None)
        shots = parse_scenes_csv(csv_path)

        if len(shots) >= target_min_scenes:
            print(f"[AutoDetect] {len(shots)} scenes found with threshold={threshold}")
            break
        else:
            print(f"[AutoDetect] Only {len(shots)} scenes at threshold={threshold}, lowering...")
            threshold -= 5  # lower sensitivity gradually

    if len(shots) < target_min_scenes:
        print("[AutoDetect] Too few scenes, using fixed-window fallback.")
        shots = fixed_window_fallback(video_path)

    json.dump(shots, open(out_dir / f"{stem}.shots.json", "w"), indent=2)
    return shots


def parse_scenes_csv(csv_path):
    shots = []
    with open(csv_path) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(",")]
            # skip header or malformed lines
            if not parts or not parts[0].isdigit() or len(parts) < 7:
                continue
            try:
                start = float(parts[3])  # Start Time (seconds)
                end = float(parts[6])    # End Time (seconds)
            except ValueError:
                continue
            if end > start:
                shots.append({
                    "shot_id": int(parts[0]),
                    "start": start,
                    "end": end
                })
    shots.sort(key=lambda s: s["start"])
    return shots

def fixed_window_fallback(video_path, window_size=10.0):
    try:
        duration = get_video_duration(video_path)
        window = 6.0
        overlap = 1.0
        shots = []
        t = 0.0
        shot_id = 1
        while t < duration:
            shots.append({"shot_id": shot_id, "start": t, "end": min(t + window, duration)})
            t += (window - overlap)
            shot_id += 1
        return shots
    except Exception as e:
        print(f"[Fallback] Error during fixed-window fallback: {e}")
        return []

def get_video_duration(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    return frame_count / fps

def time_to_seconds(tc: str) -> float:
    """Convert timecode like '00:01:23.45' or '32.24' to seconds."""
    parts = tc.strip().split(":")
    try:
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h, m, s = 0, parts[0], parts[1]
        elif len(parts) == 1:
            h, m, s = 0, 0, parts[0]
        else:
            raise ValueError(f"Unexpected timecode format: {tc}")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        print(f"[WARN] Skipping malformed timecode: {tc}")
        return 0.0