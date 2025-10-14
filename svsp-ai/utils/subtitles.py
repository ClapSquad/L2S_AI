# svsp-ai/utils/subtitles.py
from typing import List, Tuple

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
