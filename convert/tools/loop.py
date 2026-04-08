"""
Seamless loop creation via crossfade blending.
"""
from pathlib import Path

from convert.core.ffmpeg import crossfade_loop
from convert.config import DEFAULT_CROSSFADE_FRAMES


def make_seamless_loop(
    input: Path,
    output: Path,
    crossfade_frames: int = DEFAULT_CROSSFADE_FRAMES,
) -> Path:
    """
    Takes any video clip and makes it loop seamlessly by crossfading
    the end back into the beginning.

    crossfade_frames: number of frames to blend (default 15 = 0.5s at 30fps)
    """
    return crossfade_loop(input, output, crossfade_frames=crossfade_frames)
