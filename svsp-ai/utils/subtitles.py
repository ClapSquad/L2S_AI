import os, uuid, subprocess
from typing import List, Tuple


def remap_subtitles(summarized_segments):
    """
    summarized_segments: [(text, (orig_start, orig_end)), ...]
    returns: [(text, (new_start, new_end))]  # in new timeline
    """
    remapped = []
    current_time = 0.0

    for text, (orig_start, orig_end) in summarized_segments:
        seg_len = orig_end - orig_start
        new_start = current_time
        new_end = current_time + seg_len
        remapped.append((text, (new_start, new_end)))
        current_time = new_end

    return remapped


def seconds_to_srt_time(t: float) -> str:
    hours = int(t // 3600)
    minutes = int((t % 3600) // 60)
    seconds = int(t % 60)
    milliseconds = int(round((t - int(t)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def segments_to_srt(segments: List[Tuple[str, Tuple[float, float]]], srt_path: str):
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (text, (start, end)) in enumerate(segments, start=1):
            start_ts = seconds_to_srt_time(start)
            end_ts = seconds_to_srt_time(end)
            text = text.replace("\r\n", "\n").strip()
            f.write(f"{i}\n{start_ts} --> {end_ts}\n{text}\n\n")


# UPLOAD_DIR = "output"
# OUTPUT_DIR = "generated"
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)


def burn_subtitles(file_name: str, summarized_segments: List[Tuple[str, Tuple[float, float]]], video_path, output_path, burn_in: bool = True):
    """Burn or embed subtitles into the video"""
    input_path = os.path.join(video_path, file_name)

    # Step 1: Transcribe -> SRT
    srt_filename = f"{os.path.splitext(file_name)[0]}_{uuid.uuid4().hex[:6]}.srt"
    srt_path = os.path.join(output_path, srt_filename)
    segments_to_srt(summarized_segments, srt_path)

    # Step 2: Add subtitles to video
    out_video = os.path.join(output_path, f"{os.path.splitext(file_name)[0]}_subtitled.mp4")

    if burn_in:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"subtitles={srt_path}", "-c:a", "copy", out_video]
    else:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-i", srt_path, "-c", "copy", "-c:s", "mov_text", out_video]

    subprocess.run(cmd, check=True)

    return out_video
