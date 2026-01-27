import os
import sys
from moviepy import VideoFileClip

def find_video_csv_pair(directory):
    video_file = None
    csv_file = None
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        if os.path.isfile(full_path):
            if item.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')) and video_file is None:
                video_file = full_path
            elif item.lower().endswith('.csv') and csv_file is None:
                csv_file = full_path
            if video_file and csv_file:
                break
    return video_file, csv_file

def ensure_audio_extracted(video_path):
    """
    Checks if a .wav file exists for the given video path.
    If not, extracts audio from the video and saves it as .wav.
    Returns the path to the audio file, or None if extraction fails.
    """
    base_name = os.path.splitext(video_path)[0]
    audio_path = base_name + ".wav"

    if os.path.exists(audio_path):
        return audio_path

    try:
        # Extract audio using moviepy
        clip = VideoFileClip(video_path)
        if clip.audio:
            print(f"Extracting audio for: {os.path.basename(video_path)}")
            clip.audio.write_audiofile(audio_path, logger=None)
            clip.close()
            return audio_path
        else:
            clip.close()
            print(f"No audio stream found in {video_path}")
            return None
    except Exception as e:
        print(f"Error extracting audio from {video_path}: {e}")
        return None
