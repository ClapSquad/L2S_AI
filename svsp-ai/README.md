# Semantic Video Summarization Pipeline - AI

## About project

This sub-folder is ai part of [SVSP](../README.md)

## Dataset

541 Youtube video ids with heatmap data: [link](https://drive.google.com/drive/folders/1R8TQ5G1964mR8PQBy0dRVa1Y58vu0XWh)

## How to run

1. Install required python packages
```PowerShell
pip install requests openai-whisper ffmpeg-python
```

2. Run main.py at svsp/svsp-ai path
```PowerShell
python main.py
```

Current state of code receives video path then prints text of transcription.
```python
from utils.video_to_audio import convert_video_to_audio
from utils.audio_to_text import transcribe_audio
import logging, shutil, os

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    filename="log.log",
                    level=logging.DEBUG)
logging.debug("Logging started.")


def main():
    VIDEO_PATH = "{target video path}" # <- put video path that you want to test
    CACHE_PATH = "./cache"

    audio_file = convert_video_to_audio(VIDEO_PATH, CACHE_PATH)

    audio_path = os.path.join(CACHE_PATH, audio_file)
    text = transcribe_audio(audio_path)

    print(text)

    if os.path.exists(CACHE_PATH):
        shutil.rmtree(CACHE_PATH)
        logging.debug(f"Removed cache folder: {CACHE_PATH}")


if __name__ == '__main__':
    main()
```
