import os
from datasets import load_dataset
import shutil

def youtube_commons_build_data(out_csv, n_samples):
    """
    Loads and samples data from the YouTube-Commons dataset.
    """
    dataset_path = os.environ.get("PATH_TO_YOUTUBE_COMMONS")
    if dataset_path:
        print(f"Loading YouTube-Commons dataset from local path: {dataset_path}")
    else:
        print("Loading YouTube-Commons dataset from Hugging Face...")
        dataset_path = "hf://datasets/PleIAs/YouTube-Commons/cctube_0.parquet"
    ds = load_dataset("parquet", data_files=dataset_path)["train"]
    print(f"Initial dataset size: {len(ds)}")

    if n_samples is not None and n_samples < len(ds):
        print(f"Shuffling and selecting {n_samples} samples...")
        ds = ds.shuffle().select(range(n_samples))

    df = ds.to_pandas()
    df.to_csv(out_csv, index=False)
        
    return len(df)