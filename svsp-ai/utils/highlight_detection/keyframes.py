import os, pathlib, subprocess

def extract_keyframes(video_path, shots, fps=1.0):
    stem = pathlib.Path(video_path).stem
    base_dir = pathlib.Path("data/keyframes") / stem
    base_dir.mkdir(parents=True, exist_ok=True)

    for shot in shots:
        sid = f"{shot['shot_id']:04d}"
        out_dir = base_dir / f"shot_{sid}"
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(shot["start"]),
            "-to", str(shot["end"]),
            "-i", video_path,
            "-vf", f"fps={fps},scale=720:-2",
            "-q:v", "2",
            str(out_dir / f"frame_%03d.jpg")
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
