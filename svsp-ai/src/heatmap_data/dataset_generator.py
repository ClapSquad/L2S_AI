import csv, json
from crawler import get_most_watched_timestamp
import numpy as np

CONST_DATASET_FILE_NAME = "youtube_video_id_list.csv"
CONST_OUTPUT_FILE_NAME = "heatmap_dataset.jsonl"


def read_yt_video_ids_from_csv(fileName: str):
    video_ids = []
    with open(fileName, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        print("Header:", header)
        for row in reader:
            video_ids.append(row[0])
    return video_ids

# id: youtube video id
# h: heatmap
# t: timestamp
# s: highlight score
def append_result_to_jsonl(video_id, mwt, output_file):
    with open(output_file, "a", encoding="utf-8") as f:
        entry = {
            "id": video_id,
            "h": [
                {"t": round(float(ts), 2), "s": round(float(score), 3)}
                for ts, score in mwt
            ]
        }
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    np.set_printoptions(precision=2, suppress=True)
    video_ids = read_yt_video_ids_from_csv(CONST_DATASET_FILE_NAME)
    for vid in video_ids:
        print(vid)
        mwt = get_most_watched_timestamp(vid)
        if mwt is not None:
            append_result_to_jsonl(vid, mwt, CONST_OUTPUT_FILE_NAME)
            print("✅ Saved to JSON")
        else:
            print("⚠️ No heatmap data found.")


if __name__ == "__main__":
    main()
