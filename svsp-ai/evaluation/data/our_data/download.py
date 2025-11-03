import yt_dlp
import argparse
import json

# Usage
# python evaluation/data/our_data/download.py --input_file <input_jsonl> --output_folder <download_folder> [--resolution 480] [--limit 10]

def main():

    parser = argparse.ArgumentParser(description="Download videos from a list of our dataset.")
    parser.add_argument("--input_file", type=str, required=True, help="Path to the input JSONL file containing video URLs.")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the folder where videos will be downloaded.")
    parser.add_argument("--resolution", type=int, default=480, help="Maximum video resolution (height) to download (e.g., 480, 720). Default is 480.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of videos to download. Downloads all by default.")
    args = parser.parse_args()

    input_file = args.input_file
    output_folder = args.output_folder

    download_count = 0
    with open(input_file, "r") as f:
        for line in f:
            if args.limit is not None and download_count >= args.limit:
                print(f"Reached download limit of {args.limit}. Stopping.")
                break

            data = json.loads(line)
            video_id = data.get("id")

            if not video_id:
                continue

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # yt-dlp options
            ydl_opts = {
                'format': f'bestvideo[height<={args.resolution}]+bestaudio/best[height<={args.resolution}]',
                'outtmpl': f'{output_folder}/{video_id}.%(ext)s',
                'quiet': False,
                'merge_output_format': 'mp4',
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    print(f"Downloading {video_id} at max {args.resolution}p...")
                    ydl.download([video_url])
                print(f"Successfully downloaded {video_id}")
                download_count += 1
            except Exception as e:
                print(f"Failed to download {video_id}: {e}")

if __name__ == "__main__":
    main()