import argparse, os, sys

# Project root adjustment for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import pandas as pd
from youtube_commons import youtube_commons_build_data
# from utils.config import get_howto100m_path


# from qvhighlights import build_qv_sample

"""

Usage:
    python evaluation/datasets/load_data.py --n_samples 100 --min_dur 3.0 --max_dur 30.0 --out /path/to/output

Output:
    Creates a CSV file at /path/to/output/yt_commons_sample.csv containing up to 100 randomly sampled entries from the YouTube-Commons dataset,
    with durations between 3.0 and 30.0 seconds.

"""

def parse_args():
    ap = argparse.ArgumentParser(description="Prepare evaluation files from YouTube-Commons.")
    ap.add_argument("--out", default="svsp-ai/data/manifests", help="Output dir (will hold the small eval files)")
    # YouTube-Commons options
    ap.add_argument("--n_samples", type=int, default=None, help="Number of samples to extract")
    ap.add_argument("--lang", type=str, default="en", help="e.g., en, ko (optional)")
    ap.add_argument("--min_dur", type=float, default=None)
    ap.add_argument("--max_dur", type=float, default=None)
    # QV options
    # ap.add_argument("--qv_max_videos", type=int, default=None)
    return ap.parse_args()

def main():
    
    print("--- Starting data loading process ---")
    args = parse_args()
    print(f"Script arguments: {vars(args)}")

    os.makedirs(args.out, exist_ok=True)
    yt_out = os.path.join(args.out, "yt_commons.csv")
    # qv_out  = os.path.join(args.out, "qvhighlights_sample.json")

    try:
        print(f"Starting to build YouTube-Commons sample. This may take some time...")
        n_samples = youtube_commons_build_data(
            out_csv=yt_out,
            n_samples=args.n_samples,
            lang=args.lang,
            min_dur=args.min_dur,
            max_dur=args.max_dur
        )
        print(f"\n[SUCCESS] [YouTube-Commons] wrote {n_samples} rows -> {yt_out}")
    except Exception as e:
        print(f"\n[ERROR] An exception occurred during data processing: {e}")
        

    # n_qv = build_qv_sample(
    #    qv_root=args.qvhighlights,
    #    out_json=qv_out,
    #    max_videos=args.qv_max_videos,
    # )
    # print(f"[QVHighlights] wrote {n_qv} videos -> {qv_out}")

if __name__ == "__main__":
    main()
