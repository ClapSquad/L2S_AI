import os
import subprocess


def convert_video_to_audio(video_path, output_folder='.'):
    filename = os.path.basename(video_path)
    audio_filename = os.path.splitext(filename)[0] + ".mp3"
    audio_path = os.path.join(output_folder, audio_filename)

    print(f"Converting {filename} → {audio_filename} ...")

    # Run FFmpeg
    try:
        subprocess.run([
            "ffmpeg",
            "-i", video_path,
            "-q:a", "0",
            "-map", "a",
            audio_path
        ], check=True)
        print("Done^^")
    except subprocess.CalledProcessError:
        print(f"Failed to convert {filename}")


def convert_multiple_videos_into_audios(input_folder, output_folder):
    # Folders
    os.makedirs(output_folder, exist_ok=True)

    # Supported video extensions
    video_extensions = (".mp4", ".mkv", ".avi", ".mov", ".flv")

    # Find all video files
    video_files = [f for f in os.listdir(input_folder) if f.lower().endswith(video_extensions)]
    print(os.listdir(input_folder))
    if not video_files:
        print("No video files found in the folder. Please add videos to convert.")
    else:
        for filename in video_files:
            video_path = os.path.join(input_folder, filename)
            convert_video_to_audio(video_path, output_folder)
