"""Video/GIF → animated WebP via FFmpeg."""
from pathlib import Path

from convert.core.ffmpeg import _run
from convert.config import FFMPEG


def video_to_webp(
    input: Path,
    output: Path,
    fps: float | None = None,
    width: int | None = None,
    quality: int = 80,
    loop: int = 0,
) -> Path:
    """
    Convert video or GIF to animated WebP.

    Args:
        quality: 0-100, higher = better (default 80)
        loop:    0 = infinite loop, N = loop N times
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-i", str(input)]
    filters = []
    if fps is not None:
        filters.append(f"fps={fps}")
    if width is not None:
        filters.append(f"scale={width}:-2")
    if filters:
        cmd += ["-vf", ",".join(filters)]
    cmd += ["-c:v", "libwebp_anim", "-quality", str(quality), "-loop", str(loop)]
    cmd += [str(output)]
    _run(cmd)
    return output
