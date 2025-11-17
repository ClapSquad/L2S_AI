import pathlib, json, yaml
from .shot_detection import detect_shots
from .keyframes import extract_keyframes
from .feature_scoring import compute_hd_branch
from .transcript_scoring import txt_score_per_shot
from .fusion import fuse_and_select

def run_echofusion(video_path, title="", summary="", llm_timestamps=[], **overrides):
    cfg = yaml.safe_load(open(pathlib.Path(__file__).with_name("config.yaml")))
    cfg["fusion"].update({k:v for k,v in overrides.items() if k in cfg["fusion"]}) # Override fusion params as given

    # Shot Detection
    print("\n--- Step 1: Shot Detection ---")
    if not pathlib.Path(f"data/shots/{video_path.stem}.shots.json").exists():
        shots = detect_shots(video_path, init_threshold=cfg["segmentation"]["scenedetect_threshold"])
    else:
        print("-> Shots detected, loading from file.")
        shots = json.load(open(f"data/shots/{video_path.stem}.shots.json"))

    # Keyframe Extraction
    print("\n--- Step 2: Keyframe Extraction ---")
    if not (pathlib.Path("data/keyframes") / video_path.stem / "shot_0000").exists():
        print("-> Extracting keyframes ...")    
        extract_keyframes(video_path, shots, fps=cfg["segmentation"]["keyframe_fps"])
    else:
        print("-> Keyframes already extracted, skipping.")

    print("\n--- Step 3: Compute Branch Scores ---")
    print("-> HD Branch")
    hd = compute_hd_branch(video_path, shots, title, summary, cfg["hd_branch"])
    stem = pathlib.Path(video_path).stem
    hd_path = f"data/shots/{stem}.hd.json"
    json.dump(hd, open(hd_path,"w"), indent=2)
    print(f"-> Done. HD scores saved to {hd_path}")

    if not llm_timestamps:
        print("-> No LLM timestamps provided, generating via video_to_summarization ...")
        from src.core.summarization.video_to_summarization import video_to_summarization
        try:
            _, _, llm_timestamps = video_to_summarization(video_path)
        except Exception as e:
            print(f"Error generating LLM timestamps: {e}")
            llm_timestamps = []

    print("-> TXT Branch")
    txt = txt_score_per_shot(shots, llm_timestamps)
    txt_path = f"data/shots/{stem}.txt.json"
    json.dump(txt, open(txt_path,"w"), indent=2)
    print(f"-> Done. TXT scores saved to {txt_path}")

    print("\n--- Step 4: Fusion and Highlight Selection ---")
    predictions = fuse_and_select(video_path, hd_path, txt_path,
        w_hd=cfg["fusion"]["w_hd"],
        w_txt=cfg["fusion"]["w_txt"],
        w_aud=cfg["fusion"]["w_aud"],
        keep_seconds=cfg["fusion"]["keep_seconds"],
        min_len=cfg["fusion"]["min_len"],
        max_len=cfg["fusion"]["max_len"],
        merge_gap=cfg["fusion"]["merge_gap"])
    
    print("-> Done!")
    return predictions
