"""
Video/frames → GIF via gifski + gifsicle.

gifski:   high-quality palette generation + dithering
gifsicle: size optimization + optional lossy compression
"""
import subprocess
from pathlib import Path

from convert.config import GIFSKI, GIFSICLE, DEFAULT_FPS, DEFAULT_GIF_COLORS
from convert.core.ffmpeg import extract_frames, get_video_info


def frames_to_gif(
    frames: list[Path],
    output: Path,
    fps: float = DEFAULT_FPS,
    width: int | None = None,
    colors: int = DEFAULT_GIF_COLORS,
    lossy: int | None = None,
    optimize_level: int = 3,
) -> Path:
    """
    Encode a list of PNG frames to GIF using gifski then gifsicle.

    Args:
        frames:         sorted list of PNG paths
        output:         destination .gif path
        fps:            output frame rate
        width:          resize width (None = preserve)
        colors:         palette size, max 256
        lossy:          gifsicle lossy level (None = lossless, 40-100 = lossy)
        optimize_level: gifsicle -O level (1-3)
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    gifski_cmd = [
        str(GIFSKI),
        "--fps", str(fps),
        "--colors", str(min(colors, 256)),
        "--output", str(output),
    ]
    if width is not None:
        gifski_cmd += ["--width", str(width)]
    gifski_cmd += [str(f) for f in frames]

    result = subprocess.run(gifski_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"gifski failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )

    # Optimize in-place with gifsicle
    gifsicle_cmd = [
        str(GIFSICLE),
        f"-O{optimize_level}",
        "--colors", str(min(colors, 256)),
        "--batch", str(output),
    ]
    if lossy is not None:
        gifsicle_cmd += [f"--lossy={lossy}"]

    result = subprocess.run(gifsicle_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"gifsicle failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )

    return output


def video_to_gif(
    input: Path,
    output: Path,
    fps: float = DEFAULT_FPS,
    width: int | None = None,
    colors: int = DEFAULT_GIF_COLORS,
    lossy: int | None = None,
    optimize_level: int = 3,
    _frames_dir: Path | None = None,
) -> Path:
    """
    Convert a video file directly to GIF.

    Extracts frames via ffmpeg then passes them to frames_to_gif.
    Pass _frames_dir to reuse an already-extracted frame directory.
    """
    if _frames_dir is None:
        from convert.config import TEMP_DIR
        import uuid
        _frames_dir = TEMP_DIR / uuid.uuid4().hex / "frames"

    frames = extract_frames(input, _frames_dir, fps=fps)
    return frames_to_gif(
        frames, output,
        fps=fps, width=width, colors=colors,
        lossy=lossy, optimize_level=optimize_level,
    )
