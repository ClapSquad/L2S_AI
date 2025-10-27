#!/usr/bin/env python3
"""
Download videos listed in a CSV using yt-dlp.

Works when your CSV has one of these columns (any name is fine, it auto-detects):
  - url
  - video_url
  - video_link
  - link
  - id (YouTube ID like 'dQw4w9WgXcQ')

Usage examples:
  python download.py --csv yt_commons.csv
  python download.py --csv yt_commons.csv --quality 720p --out-dir output/directory
  python download.py --csv yt_commons.csv --url-col my_custom_url_col
  python download.py --csv yt_commons.csv --cookies cookies.txt

Requires:
  pip install yt-dlp
  (FFmpeg installed and on PATH for merging/format conversion)
"""

import argparse
import csv
import os
import sys
from typing import List, Optional

try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("Error: yt-dlp not installed. Install with: pip install yt-dlp")
    sys.exit(1)

QUALITY_TO_FORMAT = {
    # Prefer MP4 outputs when possible. Fallback to 'best' at that height.
    "144p":  "bestvideo[height<=144][ext=mp4]+bestaudio[ext=m4a]/best[height<=144][ext=mp4]/best[height<=144]/best",
    "240p":  "bestvideo[height<=240][ext=mp4]+bestaudio[ext=m4a]/best[height<=240][ext=mp4]/best[height<=240]/best",
    "360p":  "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]/best",
    "480p":  "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]/best",
    "720p":  "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]/best",
    "best":  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best"
}

AUTO_URL_COL_CANDIDATES = ["url", "video_url", "video_link", "link"]
ID_COL_CANDIDATES = ["id", "video_id", "youtube_id"]

def infer_columns(header: List[str], url_col: Optional[str], id_col: Optional[str]):
    lower = [h.lower() for h in header]
    chosen_url = None
    chosen_id = None

    if url_col and url_col.lower() in lower:
        chosen_url = header[lower.index(url_col.lower())]
    if id_col and id_col.lower() in lower:
        chosen_id = header[lower.index(id_col.lower())]

    if chosen_url is None:
        for c in AUTO_URL_COL_CANDIDATES:
            if c in lower:
                chosen_url = header[lower.index(c)]
                break
    if chosen_id is None:
        for c in ID_COL_CANDIDATES:
            if c in lower:
                chosen_id = header[lower.index(c)]
                break
    return chosen_url, chosen_id

def row_to_url(row, url_col: Optional[str], id_col: Optional[str]) -> Optional[str]:
    # Priority: explicit URL column if present.
    if url_col and row.get(url_col):
        return row[url_col].strip()

    # Else try to build from ID if present.
    if id_col and row.get(id_col):
        vid = row[id_col].strip()
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"

    # Else try any URL-ish field we can find.
    for k, v in row.items():
        if not v:
            continue
        v = v.strip()
        if v.startswith("http://") or v.startswith("https://"):
            return v
    return None

def main():
    parser = argparse.ArgumentParser(description="Download videos from CSV via yt-dlp.")
    parser.add_argument("--csv", required=True, help="Path to the CSV file (e.g., yt_commons.csv)")
    parser.add_argument("--out-dir", default="downloads", help="Output directory (default: downloads)")
    parser.add_argument("--quality", default="480p", choices=list(QUALITY_TO_FORMAT.keys()),
                        help="Target quality (default: 480p)")
    parser.add_argument("--url-col", default=None, help="Name of the URL column if your CSV uses a custom header")
    parser.add_argument("--id-col", default=None, help="Name of the YouTube ID column if your CSV uses a custom header")
    parser.add_argument("--limit", type=int, default=None, help="Download at most N rows")
    parser.add_argument("--start", type=int, default=0, help="Start from this row index (0-based)")
    parser.add_argument("--cookies", default=None, help="Path to cookies.txt if needed (may help with 403/age gates)")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"CSV not found: {args.csv}")
        sys.exit(1)

    os.makedirs(args.out_dir, exist_ok=True)

    # Build format string from chosen quality
    fmt = QUALITY_TO_FORMAT[args.quality]

    # Some headers and extractor args that often help with 403 / throttling on YouTube
    # (These are safe to keep; yt-dlp ignores what it doesn't need.)
    http_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    ydl_opts = {
        "outtmpl": os.path.join(args.out_dir, "%(id)s.%(ext)s"),
        "format": fmt,
        "merge_output_format": "mp4",
        "restrictfilenames": True,
        "noprogress": False,
        "quiet": False,
        "ignoreerrors": True,           # Skip problematic videos but keep going
        "retries": 5,
        "fragment_retries": 5,
        "continuedl": True,
        "concurrent_fragment_downloads": 2,
        "http_headers": http_headers,
        # Sometimes helps avoid 403 / signature issues on YT
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        # Uncomment this if you see a lot of "HTTP Error 403: Forbidden"
        # "throttledratelimit": 1024 * 1024,  # 1 MB/s; can help with YT throttling
    }

    if args.cookies:
        if not os.path.exists(args.cookies):
            print(f"cookies.txt not found: {args.cookies}")
            sys.exit(1)
        ydl_opts["cookiefile"] = args.cookies

    # Read CSV rows and infer URL/ID columns
    urls: List[str] = []
    with open(args.csv, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("The CSV seems to have no header row. Please add headers or use a proper CSV.")
            sys.exit(1)

        url_col, id_col = infer_columns(reader.fieldnames, args.url_col, args.id_col)
        if not url_col and not id_col:
            print(
                "Could not find a URL or ID column.\n"
                "Add a header like 'url' or 'id', or pass --url-col / --id-col."
            )
            sys.exit(1)

        for i, row in enumerate(reader):
            if i < args.start:
                continue
            if args.limit is not None and len(urls) >= args.limit:
                break

            url = row_to_url(row, url_col, id_col)
            if url:
                urls.append(url)

    if not urls:
        print("No valid URLs found in the CSV after scanning rows.")
        sys.exit(0)

    print(f"Found {len(urls)} videos to download (quality={args.quality}).")
    with YoutubeDL(ydl_opts) as ydl:
        # Download one by one so a single failure doesn't stop the batch
        for idx, link in enumerate(urls, 1):
            print(f"[{idx}/{len(urls)}] Downloading: {link}")
            try:
                ydl.download([link])
            except Exception as e:
                # Keep going even if this one fails
                print(f"  -> Failed: {link}\n     Reason: {e}")

    print("Done.")
    print(f"Files saved in: {os.path.abspath(args.out_dir)}")

if __name__ == "__main__":
    main()
