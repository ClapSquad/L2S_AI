# Takes a video file and a list of timestamps, 
# cuts the video into segments based on the timestamps,

import os
import logging
from typing import List, Tuple
import ffmpeg


def cut_video_by_timestamps(video_path: str, timestamps: List[Tuple[float, float]], output_path: str):
    """
    Cuts a video into segments based on timestamps and concatenates them.

    Args:
        video_path (str): Path to the input video file.
        timestamps (list): A list of (start_time, end_time) tuples in seconds.
        output_path (str): Path to save the final concatenated video.
    """
    
    # timestamps is a list of (start, end) tuples
    if not timestamps:
        logging.warning("No timestamps provided for video cutting. Skipping.")
        return

    if not os.path.exists(video_path):
        logging.error(f"Input video not found at: {video_path}")
        raise FileNotFoundError(f"Input video not found at: {video_path}")

    try:
        input_stream = ffmpeg.input(video_path)
        video_segments = []
        audio_segments = []

        # iterates  through each (start, end) tuple in timestamps
        for i, (start, end) in enumerate(timestamps):
            logging.debug(f"Preparing segment {i}: from {start}s to {end}s")
            # Using trim and atrim filters. setpts/asetpts are crucial for correct concatenation.

            # trims both the video and audio streams to the specified start and end times
            
            # PTS-STARTPTS resets the timestamps to start from zero for each segment
            # without this when concatenating, there would be large gaps of black video/audio
            # corresponding to the parts of the original video that were cut out

            video_segments.append(
                input_stream.video.trim(start=start, end=end).setpts('PTS-STARTPTS')
            )
            audio_segments.append(
                input_stream.audio.filter('atrim', start=start, end=end).filter('asetpts', 'PTS-STARTPTS')
            ) 
            # filter applies atrim and asetpts to the audio stream
            # atrim trims the audio to the specified start and end times
            # asetpts resets the audio timestamps to start from zero for each segment

        # Concatenate all video and audio segments
        concatenated_video = ffmpeg.concat(*video_segments, v=1, a=0)
        concatenated_audio = ffmpeg.concat(*audio_segments, v=0, a=1)

        # Combine the concatenated video and audio streams into the final output file
        (
            ffmpeg
            .output(concatenated_video, concatenated_audio, output_path, vcodec='libx264', acodec='aac')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        logging.info(f"Successfully created summarized video at: {output_path}")

    except ffmpeg.Error as e:
        logging.error("ffmpeg error occurred:")
        logging.error(e.stderr.decode())
        raise