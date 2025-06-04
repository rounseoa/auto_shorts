"""Everything is accessible from the top-level moviepy module."""
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.VideoClip import ColorClip, ImageClip, TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from moviepy.video.fx.all import *
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.audio.fx.all import *

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

# Export most used classes/functions for convenience
__all__ = [
    "VideoFileClip",
    "ColorClip",
    "ImageClip",
    "TextClip",
    "CompositeVideoClip",
    "concatenate_videoclips",
    "AudioFileClip",
    "AudioArrayClip",
    "ffmpeg_extract_subclip",
]
