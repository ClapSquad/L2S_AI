# L2S: Long2Short Video Sumammarization

This repo contains a modular pipeline designed to automatically analyze video content, detect the most significant highlights, and generate a concise summary. It leverages a decoupled, interface-based architecture that allows for easy extension and customization, making it simple to swap in different algorithms for detection and summarization.

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Core Concepts](#core-concepts)
- [LLM vs EchoFusion](#llm-vs-echofusion)
  - [LLM Method](#llm-method)
    - [Pipeline Flow](#pipeline-flow)
    - [Detailed Steps](#detailed-steps)
    - [Key Features](#key-features)
    - [Potential Use Cases](#potential-use-cases)
  - [EchoFusion Method](#echofusion-method)
    - [Pipeline Flow](#pipeline-flow-1)
    - [Detailed Steps](#detailed-steps-1)
    - [Configurable Parameters](#configurable-parameters)
    - [Key Features](#key-features-1)
    - [Potential Use Cases](#potential-use-cases-1)
- [Method Comparison](#method-comparison)
- [Usage Examples](#usage-examples)



## Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

1. Docker is recommmended. Otherwise, you can use Anaconda or Python environments.

### Installation

1.  Clone the repository:
2. Create an `.env` file (see `.env.example`)
3. If using Docker, build the image and run it like this:

Download the base image:

```bash
docker pull runpod/pytorch:1.0.2-cu1281-torch271-ubuntu2204
```

To build the container:

```bash
docker build -t l2s-ai . # build the container
```

To run the container:
- If you don't have an NVIDIA GPU, run: 

```bash
docker run --rm -it -p 8080:8080 --env-file .env -v .:/app l2s-ai # run the container
```

- If you have NVIDIA GPU, run

```bash
docker run --gpus all -it --rm -v .:/app -p 8080:8080 --env-file .env l2s-ai # run the container
```


## Core Concepts

The pipeline is composed of three primary components:

1.  **`core`**: The heart of the application. It contains the orchestration logic, data models, and interfaces that define the pipeline's structure. It is responsible for managing the workflow from start to finish.

2.  **`highlight_detection`**: A specialized module responsible for analyzing the input content (e.g., a video) and identifying the most important segments. This could be based on audio cues, visual action, or semantic meaning from a transcript.

3.  **`summarization`**: This module takes the detected highlight segments and condenses them into a short, human-readable summary. It can use extractive methods (stitching clips together) or abstractive methods (generating new text).

The `main.py` script offers two distinct methods for video summarization and highlight detection, each optimized for different use cases and quality requirements.

### LLM vs EchoFusion

1. **LLM Method** (Default): Fast, transcript-based summarization using AI language models
2. **EchoFusion Method**: Advanced multi-modal fusion combining visual features, transcript analysis, and audio cues

#### LLM Method

The LLM method is a streamlined, AI-powered approach that relies primarily on transcript analysis. This is the default method and is ideal for quick processing and content-driven summarization.

##### Pipeline Flow

```
Video Input
    ↓
1. Video to Audio Conversion
    ↓ (src/core/video_processing/video_to_audio.py)
2. Audio Transcription
    ↓ (src/core/audio_processing/audio_to_text.py)
3. LLM Timestamp Selection
    ↓ (src/core/summarization/video_to_summarization.py)
4. Hook Title Generation
    ↓
Output: Timestamps + Title
```

##### Detailed Steps

**Step 1: Audio Extraction**
- Converts video to audio format using FFmpeg
- Stores temporary audio file in cache directory

**Step 2: Transcription**
- Transcribes audio to text with timestamps
- Returns segments as: `[(text, (start_time, end_time)), ...]`

**Step 3: LLM-Based Timestamp Selection**
- Sends transcribed segments to Gemini 2.5 Flash model
- LLM analyzes content and selects most important segments
- Constraints enforced:
  - Total duration ≤ 60 seconds
  - Each segment ≥ 2 seconds
  - Non-overlapping timestamps
  - Merges adjacent segments (< 0.75s gap)
- Returns JSON: `{"timestamps": [[start, end], ...]}`

**Step 4: Hook Title Generation**
- Extracts text from selected segments
- Uses LLM to generate catchy, viral-style title (≤ 10 words)
- Constraints: alphanumeric characters only, no punctuation or emojis

**Step 5: Video Cutting**
- Uses selected timestamps to cut and concatenate video segments
- Produces final summarized video

##### Key Features
- **Fast processing**: Single-pass transcript analysis
- **Context-aware**: LLM understands semantic importance
- **Customizable**: Easy to modify prompts for different content types
- **Efficient**: Lower computational requirements

##### Potential Use Cases
- News content
- Educational videos
- Podcasts/interviews
- Meeting recordings
- Any speech-heavy content

#### EchoFusion Method

The EchoFusion method is a multi-branch fusion system that combines visual, textual, and audio features to detect highlights. 

##### Pipeline Flow

```
Video Input
    ↓
1. Shot Detection
    ↓ (src/core/highlight_detection/shot_detection.py)
2. Keyframe Extraction
    ↓ (src/core/highlight_detection/keyframes.py)
3a. HD Branch (Visual)     3b. TXT Branch (Transcript)
    ↓                           ↓
    Feature Scoring             LLM Overlap Scoring
    ↓                           ↓
4. Multi-Modal Fusion
    ↓ (src/core/highlight_detection/fusion.py)
5. Highlight Selection & Merging
    ↓
Output: Ranked Highlights
```

##### Detailed Steps

**Step 1: Shot Detection**
- Uses PySceneDetect to identify shot boundaries
- Configurable threshold for scene change sensitivity
- Saves shot metadata: `{"shot_id": int, "start": float, "end": float}`
- Cached in `data/shots/{video_name}.shots.json`

**Step 2: Keyframe Extraction**
- Extracts keyframes from each shot at configurable FPS
- Stores frames in `data/keyframes/{video_name}/shot_XXXX/`
- Used for visual feature analysis

**Step 3a: HD Branch (Visual Feature Scoring)**
- Computes visual highlight scores for each shot
- Features analyzed:
  - Visual quality (blur detection, composition)
  - Motion intensity
  - Object detection
  - Scene aesthetics
- Produces normalized HD scores: `{"shot_id": int, "HD": float, ...}`
- Saved to `data/shots/{video_name}.hd.json`

**Step 3b: TXT Branch (Transcript Scoring)**
- Uses LLM-selected timestamps from `video_to_summarization()`
- Computes overlap between each shot and important transcript segments
- Scores shots based on content relevance
- Produces TXT scores: `{"shot_id": int, "TXT": float}`
- Saved to `data/shots/{video_name}.txt.json`

**Step 4: Multi-Modal Fusion**
- Normalizes all branch scores to [0, 1] range
- Computes weighted fusion score for each shot:
  ```
  final_score = (w_hd × HD) + (w_txt × TXT) + (w_aud × AUD)
  ```
  Default weights: `w_hd=0.55, w_txt=0.45, w_aud=0.00`
- Ranks shots by final score

**Step 5: Highlight Selection & Merging**
- Selects top-ranked shots up to `keep_seconds` duration (default: 60s)
- Sorts selected shots chronologically
- Merges adjacent shots if gap < `merge_gap` (default: 1.0s)
- Applies length constraints:
  - Minimum segment length: `min_len` (default: 2.0s)
  - Maximum segment length: `max_len` (default: 10.0s)
- Returns ranked highlights: `[[start, end, score, rank], ...]`

##### Configurable Parameters

All parameters are defined in [src/core/highlight_detection/config.yaml](src/core/highlight_detection/config.yaml):

**Segmentation:**
- `scenedetect_threshold`: Shot detection sensitivity
- `keyframe_fps`: Frame extraction rate

**HD Branch:**
- Feature extraction settings
- Model configurations

**Fusion:**
- `w_hd`: Weight for visual features (0.55)
- `w_txt`: Weight for transcript features (0.45)
- `w_aud`: Weight for audio features (0.00, currently disabled)
- `keep_seconds`: Total highlight duration (60.0)
- `min_len`: Minimum segment length (2.0)
- `max_len`: Maximum segment length (10.0)
- `merge_gap`: Gap threshold for merging (1.0)

##### Key Features
- **Multi-modal analysis**: Combines visual, textual, and audio signals
- **Research-backed**: Based on academic highlight detection methods
- **Highly customizable**: Extensive configuration options
- **Reproducible**: Caches intermediate results for faster iteration

##### Potential Use Cases
- Sports highlights
- Action-heavy content
- Cinematic videos
- Content requiring visual analysis
- Multi-speaker events with visual cues

### Method Comparison

| Feature | LLM Method | EchoFusion Method |
|---------|-----------|-------------------|
| Speed | Fast | Slower (more processing) |
| Complexity | Low | High |
| Dependencies | Transcript only | Visual + Transcript + Audio |
| Best For | Speech-heavy content | Visually-driven content |
| Customization | Prompt engineering | Multi-parameter tuning |
| Computational Cost | Low | High |

### Usage Examples

**LLM Method:**
```bash
python src/main.py -f input.mp4 --method llm --vertical_export
```

**EchoFusion Method:**
```bash
python src/main.py -f input.mp4 --method echofusion --title "Video Title" --w_hd 0.6 --w_txt 0.4 --keep_seconds 90
```
