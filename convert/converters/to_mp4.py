"""
GIF/frames → H.265 MP4 via FFmpeg NVENC.

NVENC (hevc_nvenc) offloads encode to the GPU video engine,
freeing the CPU for gifski/gifsicle/ImageMagick work in parallel.
"""
from pathlib import Path

from convert.core.ffmpeg import frames_to_video, video_to_mp4 as _video_to_mp4


def frames_to_mp4(
    frames_dir: Path,
    output: Path,
    fps: float,
    nvenc: bool = True,
    crf: int = 18,
) -> Path:
    """Encode a directory of PNG frames to H.265 MP4."""
    return frames_to_video(frames_dir, output, fps=fps, nvenc=nvenc, crf=crf)


def video_to_mp4(
    input: Path,
    output: Path,
    fps: float | None = None,
    width: int | None = None,
    nvenc: bool = True,
    crf: int = 18,
) -> Path:
    """Re-encode any video (MP4, GIF, WebM, etc.) to H.265 MP4."""
    return _video_to_mp4(input, output, fps=fps, width=width, nvenc=nvenc, crf=crf)
