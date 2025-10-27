import os
from datasets import load_dataset
import shutil

def youtube_commons_build_data(out_csv, n_samples, lang, min_dur, max_dur):
    """
    Loads and samples data from the YouTube-Commons dataset.

    It will first check for a `YOUTUBE_COMMONS_DATA_PATH` environment variable
    for a local path to the dataset. If not found, it will download it from
    Hugging Face.
    """
    dataset_path = os.environ.get("PATH_TO_YOUTUBE_COMMONS")
    if dataset_path:
        print(f"Loading YouTube-Commons dataset from local path: {dataset_path}")
    else:
        print("Loading YouTube-Commons dataset from Hugging Face...")
        dataset_path = "hf://datasets/PleIAs/YouTube-Commons/cctube_0.parquet"
    ds = load_dataset("parquet", data_files=dataset_path)["train"]
    print(f"Initial dataset size: {len(ds)}")

    if lang:
        print(f"Filtering for language: {lang}")
        ds = ds.filter(lambda r: r["original_language"] == lang and r["transcription_language"] == lang)
        print(f"Size after language filter: {len(ds)}")

    # if min_dur is not None or max_dur is not None:
    #     print(f"Filtering for duration between {min_dur}s and {max_dur}s...")
    #     ds = ds.filter(lambda r: (min_dur or 0) <= (r["end"] - r["start"]) <= (max_dur or float('inf')))
    #     print(f"Size after duration filter: {len(ds)}")

    if n_samples is not None and n_samples < len(ds):
        print(f"Shuffling and selecting {n_samples} samples...")
        ds = ds.shuffle().select(range(n_samples))

    df = ds.to_pandas()
    df.to_csv(out_csv, index=False)
        
    return len(df)