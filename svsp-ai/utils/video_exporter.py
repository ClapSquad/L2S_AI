import subprocess
import os

def export_social_media_vertical_video(input_path, output_path, resolution="1080x1920", bitrate="15M"):
    """
    주어진 입력 비디오를 9:16 수직형 MP4로 내보냅니다.
    - 남는 공간은 원본 영상의 블러 처리된 복사본으로 채웁니다. (전문적인 소셜 미디어 배경)
    - FFmpeg을 사용하여 비디오를 변환합니다.

    Args:
        input_path (str): 입력 비디오 파일 경로
        output_path (str): 출력 비디오 파일 경로
        resolution (str): 출력 해상도 (기본값: 1080x1920)
        bitrate (str): 출력 비트레이트 (기본값: 15M - 15 Mbps, 고품질)
    """

    # 1. FFmpeg 필터 그래프 구축
    filter_complex = (
        # 1. 원본 스트림 분할: [main]은 선명한 전경, [bg]는 블러 배경용
        "[0:v]split=2[main][bg];"

        # 2. 블러 배경 스트림 생성 [blurry_bg]
        "[bg]scale=w=1080:h=1920:force_original_aspect_ratio=increase,boxblur=20:10,crop=1080:1920[blurry_bg];" 

        # 3. 메인 영상 스트림 생성 [main_scaled]
        "[main]scale=w=1080:h=1920:force_original_aspect_ratio=decrease[main_scaled];"

        # 4. 최종 오버레이 [v]
        "[blurry_bg][main_scaled]overlay=(W-w)/2:(H-h)/2[v]"
    )

    # 2. FFmpeg 명령어 구성 (보안 강화: 리스트 형식)
    command = [
        "ffmpeg",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-b:v", bitrate,
        "-pix_fmt", "yuv420p",
        "-s", resolution,
        "-c:a", "aac",
        "-b:a", "192k",
        "-y",
        output_path
    ]

   # 3. FFmpeg 실행
    print(f"\n--- Starting Social Media Export for {os.path.basename(input_path)} ---")
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"✅ Export Successful: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg Error: Export failed for {input_path}")
        print(f"  Error Details: {e.stderr.strip()}")
        raise
    except FileNotFoundError:
        print("❌ Error: FFmpeg command not found. Ensure FFmpeg is installed and in your system PATH.")
        raise