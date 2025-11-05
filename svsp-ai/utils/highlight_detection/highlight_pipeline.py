import pathlib, json, yaml
from .shot_detection import detect_shots
from .keyframes import extract_keyframes
from .scoring import compute_hd_branch
from .txt_branch import txt_score_per_shot
from .fusion import fuse_and_select

def run_echofusion(video_path, title="", summary="", llm_timestamps=[], **overrides):
    cfg = yaml.safe_load(open(pathlib.Path(__file__).with_name("config.yaml")))
    cfg["fusion"].update({k:v for k,v in overrides.items() if k in cfg["fusion"]}) # Override fusion params as given

    print("\n--- Step 1: Shot Detection & Keyframe Extraction ---")
    shots = detect_shots(video_path, init_threshold=cfg["segmentation"]["scenedetect_threshold"])
    print("-> Extracting Keyframes ...")
    extract_keyframes(video_path, shots, fps=cfg["segmentation"]["keyframe_fps"])

    print("\n--- Step 2: Compute Branch Scores ---")
    print("-> HD Branch")
    hd = compute_hd_branch(video_path, shots, title, summary, cfg["hd_branch"])
    stem = pathlib.Path(video_path).stem
    hd_path = f"data/shots/{stem}.hd.json"
    json.dump(hd, open(hd_path,"w"), indent=2)
    print(f"-> Done. HD scores saved to {hd_path}")

    if not llm_timestamps:
        print("-> No LLM timestamps provided, generating via video_to_summarization ...")
        from utils.video_to_summarization import video_to_summarization
        _, _, llm_timestamps = video_to_summarization(video_path)

    print("-> TXT Branch")
    txt = txt_score_per_shot(shots, llm_timestamps)
    txt_path = f"data/shots/{stem}.txt.json"
    json.dump(txt, open(txt_path,"w"), indent=2)
    print(f"-> Done. TXT scores saved to {txt_path}")
    
    print("\n--- Step 3: Fusion and Highlight Selection ---")
    predictions = fuse_and_select(video_path, hd_path, txt_path,
        w_hd=cfg["fusion"]["w_hd"],
        w_txt=cfg["fusion"]["w_txt"],
        w_aud=cfg["fusion"]["w_aud"],
        keep_seconds=cfg["fusion"]["keep_seconds"],
        min_len=cfg["fusion"]["min_len"],
        max_len=cfg["fusion"]["max_len"],
        merge_gap=cfg["fusion"]["merge_gap"])
    
    return predictions
