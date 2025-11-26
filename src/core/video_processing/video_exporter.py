import subprocess
import os


def export_social_media_vertical_video(input_path, output_path, resolution="1080x1920", bitrate="15M", crop_method="center"):
    """
    Exports a given input video to a 9:16 vertical MP4.
    - crop_method='center': Crops the central 9:16 area.
    - crop_method='blur': Fills the remaining space with a blurred copy of the original video.
    """
    # Parse and validate the resolution string
    try:
        width, height = map(int, resolution.split('x'))
    except ValueError:
        raise ValueError(f"Invalid resolution format: {resolution}. Expected 'widthxheight'.")

    if crop_method == "blur":
        # 1. Build FFmpeg filter graph (blur background)
        filter_complex = (
            # 1. Split the original stream
            f"[0:v]split=2[main][bg];"
            # 2. Create the blurred background stream
            f"[bg]scale=w={width}:h={height}:force_original_aspect_ratio=increase,boxblur=20:10,crop={width}:{height}[blurry_bg];"
            # 3. Create the main video stream
            f"[main]scale=w={width}:h={height}:force_original_aspect_ratio=decrease[main_scaled];"
            # 4. Final overlay
            f"[blurry_bg][main_scaled]overlay=(W-w)/2:(H-h)/2[v]"
        )
    elif crop_method == "center":
        # 1. Build FFmpeg filter graph (center crop)
        target_aspect_ratio = width / height
        filter_complex = (
            f"[0:v]crop=ih*{target_aspect_ratio}:ih,scale={width}:{height}[v]"
        )
    else:
        raise ValueError(f"Invalid crop_method: '{crop_method}'. Choose 'center' or 'blur'.")


    # 2. Configure FFmpeg command
    command = [
        "ffmpeg",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",

        # Encoding settings
        "-c:v", "libx264",
        "-b:v", bitrate,
        "-pix_fmt", "yuv420p",
        "-s", resolution,  # Set final resolution
        "-c:a", "aac",
        "-b:a", "192k",
        "-y",
        output_path
    ]

    # 3. Run FFmpeg
    print(f"\n--- Starting Vertical Export for {os.path.basename(input_path)} ---")
    try:
        # Capture stdout and stderr
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"✅ Export Successful: {output_path}")

    # On CalledProcessError, print both STDOUT and STDERR
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg Error: Export failed for {input_path}")
        print(f"  STDOUT: {e.stdout.strip()}")  # Print STDOUT
        print(f"  STDERR: {e.stderr.strip()}")
        raise
    except FileNotFoundError:
        print("❌ Error: FFmpeg command not found. Ensure FFmpeg is installed and in your system PATH.")
        raise