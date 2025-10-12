import subprocess
import os


def export_social_media_vertical_video(input_path, output_path, resolution="1080x1920", bitrate="15M"):
    """
    주어진 입력 비디오를 9:16 수직형 MP4로 내보냅니다.
    - 남는 공간은 원본 영상의 블러 처리된 복사본으로 채웁니다.
    - 해상도 매개변수를 동적으로 사용하여 FFmpeg 필터 그래프를 구성합니다.
    """

    # 피드백 1 반영: 해상도 문자열 파싱 및 유효성 검사
    try:
        width, height = map(int, resolution.split('x'))
    except ValueError:
        raise ValueError(f"Invalid resolution format: {resolution}. Expected 'widthxheight'.")

    # 1. FFmpeg 필터 그래프 구축 (동적 변수 사용)
    filter_complex = (
        # 1. 원본 스트림 분할
        f"[0:v]split=2[main][bg];"

        # 2. 블러 배경 스트림 생성 [blurry_bg] (동적 {width}, {height} 사용)
        f"[bg]scale=w={width}:h={height}:force_original_aspect_ratio=increase,boxblur=20:10,crop={width}:{height}[blurry_bg];"

        # 3. 메인 영상 스트림 생성 [main_scaled] (동적 {width}, {height} 사용)
        f"[main]scale=w={width}:h={height}:force_original_aspect_ratio=decrease[main_scaled];"

        # 4. 최종 오버레이 [v]
        f"[blurry_bg][main_scaled]overlay=(W-w)/2:(H-h)/2[v]"
    )

    # 2. FFmpeg 명령어 구성
    command = [
        "ffmpeg",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a",

        # 인코딩 설정
        "-c:v", "libx264",
        "-b:v", bitrate,
        "-pix_fmt", "yuv420p",
        "-s", resolution,  # 최종 해상도 설정
        "-c:a", "aac",
        "-b:a", "192k",
        "-y",
        output_path
    ]

    # 3. FFmpeg 실행
    print(f"\n--- Starting Social Media Export for {os.path.basename(input_path)} ---")
    try:
        # stdout과 stderr를 캡처
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"✅ Export Successful: {output_path}")

    # 피드백 3 반영: CalledProcessError 발생 시 STDOUT과 STDERR 모두 출력
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg Error: Export failed for {input_path}")
        print(f"  STDOUT: {e.stdout.strip()}")  # STDOUT 추가 출력
        print(f"  STDERR: {e.stderr.strip()}")
        raise
    except FileNotFoundError:
        print("❌ Error: FFmpeg command not found. Ensure FFmpeg is installed and in your system PATH.")
        raise