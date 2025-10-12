from utils.video_to_summarization import video_to_summarization
from utils.logging_initialization import initialize_logging
from utils.video_processor import cut_video_by_timestamps
from utils.video_exporter import export_social_media_vertical_video
import os
import argparse
import subprocess  # subprocess.CalledProcessError 사용을 위해 임포트


def main():
    initialize_logging()
    parser = argparse.ArgumentParser(description="Video summarization script")
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to the input video file")
    parser.add_argument("-v", "--vertical_export", action="store_true",
                        help="Exports a vertical (9:16) video optimized for social media.")
    args = parser.parse_args()

    VIDEO_PATH = args.file
    OUTPUT_PATH = "./output"
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    base_filename = os.path.splitext(os.path.basename(VIDEO_PATH))[0]

    SUMMARIZED_VIDEO_PATH = os.path.join(OUTPUT_PATH, f"{base_filename}_summary.mp4")

    summary_text, timestamps = video_to_summarization(VIDEO_PATH)
    cut_video_by_timestamps(VIDEO_PATH, timestamps, SUMMARIZED_VIDEO_PATH)

    if args.vertical_export:
        VERTICAL_EXPORT_PATH = os.path.join(OUTPUT_PATH, f"{base_filename}_reel.mp4")

        # 피드백 2 반영: 구체적인 오류부터 처리
        try:
            print("\n--- Starting Social Media Export Step ---")
            export_social_media_vertical_video(
                input_path=SUMMARIZED_VIDEO_PATH,
                output_path=VERTICAL_EXPORT_PATH
            )
            print(f"\n✨ Pipeline Complete. Final Vertical Video: {VERTICAL_EXPORT_PATH}")

        except subprocess.CalledProcessError as e:
            # FFmpeg 명령 자체의 실패
            print(f"\n🚨 Vertical export step failed (FFmpeg Command Error). Check error details above.")
            # 이 오류는 video_exporter.py에서 이미 상세 내용을 출력하고 raise 했으므로 간단히 알림

        except FileNotFoundError:
            # FFmpeg 실행 파일 또는 입력 파일 없음
            print(f"\n🚨 Vertical export step failed (File Not Found Error). Check FFmpeg installation or input path.")

        except ValueError as e:
            # video_exporter.py에서 해상도 포맷이 잘못되었을 때 발생하는 오류
            print(f"\n🚨 Vertical export step failed (Invalid Parameter Error): {e}")

        except Exception as e:
            # 예상치 못한 기타 오류 (Fallback)
            print(f"\n🚨 Vertical export step failed (Unexpected Error): {e}")


    elif os.path.exists(SUMMARIZED_VIDEO_PATH):
        print(f"\n✨ Pipeline Complete. Summarized Video: {SUMMARIZED_VIDEO_PATH}")


if __name__ == '__main__':
    main()