"""Video/GIF → APNG via FFmpeg."""
from pathlib import Path

from convert.core.ffmpeg import _run
from convert.config import FFMPEG


def video_to_apng(
    input: Path,
    output: Path,
    fps: float | None = None,
    width: int | None = None,
    plays: int = 0,
) -> Path:
    """
    Convert video or GIF to APNG.

    Args:
        plays: 0 = infinite loop, N = play N times
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
    cmd += ["-f", "apng", "-plays", str(plays)]
    cmd += [str(output)]
    _run(cmd)
    return output
