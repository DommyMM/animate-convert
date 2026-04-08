"""
All FFmpeg subprocess wrappers.

Every function returns a Path to its output. Raises RuntimeError with
ffmpeg's stderr on non-zero exit so callers get useful error messages.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from convert.config import FFMPEG, FFPROBE, HWACCEL_DECODE_ARGS, NVENC_H265_ARGS


def _run(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [str(c) for c in cmd],
        capture_output=True,
        text=True,
        **kwargs,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )
    return result


def get_video_info(input: Path) -> dict:
    """Return fps, width, height, duration, frame_count via ffprobe."""
    result = _run([
        FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams",
        "-select_streams", "v:0", str(input),
    ])
    data = json.loads(result.stdout)
    stream = data["streams"][0]

    # fps as float — stored as "num/den" string
    num, den = stream["r_frame_rate"].split("/")
    fps = float(num) / float(den)

    duration = float(stream.get("duration", 0))
    frame_count = int(stream.get("nb_frames", 0)) or int(duration * fps)

    return {
        "fps": fps,
        "width": stream["width"],
        "height": stream["height"],
        "duration": duration,
        "frame_count": frame_count,
    }


def extract_frames(input: Path, output_dir: Path, fps: float | None = None) -> list[Path]:
    """Extract frames from a video as PNG files. Returns sorted list of frame paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y"]
    cmd += ["-i", str(input)]
    if fps is not None:
        cmd += ["-vf", f"fps={fps}"]
    cmd += [str(output_dir / "frame_%06d.png")]
    _run(cmd)
    return sorted(output_dir.glob("frame_*.png"))


def frames_to_video(
    frames_dir: Path,
    output: Path,
    fps: float,
    nvenc: bool = True,
    crf: int = 18,
) -> Path:
    """Reassemble PNG frames into an MP4."""
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-framerate", str(fps), "-i", str(frames_dir / "frame_%06d.png")]
    if nvenc:
        cmd += NVENC_H265_ARGS
    else:
        cmd += ["-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p"]
    cmd += [str(output)]
    _run(cmd)
    return output


def video_to_mp4(
    input: Path,
    output: Path,
    fps: float | None = None,
    width: int | None = None,
    nvenc: bool = True,
    crf: int = 18,
) -> Path:
    """Re-encode a video to MP4, optionally changing fps/width."""
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y"]
    if nvenc:
        cmd += HWACCEL_DECODE_ARGS
    cmd += ["-i", str(input)]
    filters = []
    if fps is not None:
        filters.append(f"fps={fps}")
    if width is not None:
        filters.append(f"scale={width}:-2")
    if filters:
        cmd += ["-vf", ",".join(filters)]
    if nvenc:
        cmd += NVENC_H265_ARGS
    else:
        cmd += ["-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p"]
    cmd += [str(output)]
    _run(cmd)
    return output


def pad_crop_to(input: Path, output: Path, width: int, height: int) -> Path:
    """Scale + pad/crop frames directory or single video to exact target resolution."""
    output.parent.mkdir(parents=True, exist_ok=True)
    # Scale to fit within target, then pad to exact size with black bars
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )
    cmd = [FFMPEG, "-y", "-i", str(input), "-vf", vf, "-c:v", "copy", str(output)]
    # copy won't work after vf — re-encode with nvenc
    cmd = [FFMPEG, "-y", "-i", str(input), "-vf", vf] + NVENC_H265_ARGS + [str(output)]
    _run(cmd)
    return output


def crossfade_loop(input: Path, output: Path, crossfade_frames: int = 15) -> Path:
    """
    Create a seamless loop by crossfading the end of the clip into its beginning.

    Takes the last N frames, blends them with the first N frames using a linear
    alpha ramp, replaces the first N frames with the blend, drops the last N frames.
    Net result: a shorter clip that loops without a hard cut.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    info = get_video_info(input)
    fps = info["fps"]
    n = crossfade_frames
    fade_duration = n / fps

    # FFmpeg xfade filter for seamless loop:
    # Trim the clip to total-fade_duration, then xfade the end with the beginning
    total_dur = info["duration"]
    offset = total_dur - fade_duration

    vf = (
        f"[0:v]split=2[main][copy];"
        f"[copy]trim=0:{fade_duration},setpts=PTS-STARTPTS[start];"
        f"[main]trim=0:{offset},setpts=PTS-STARTPTS[body];"
        f"[body][start]xfade=transition=fade:duration={fade_duration}:offset={offset - fade_duration}[out]"
    )
    cmd = [FFMPEG, "-y", "-i", str(input), "-filter_complex", vf, "-map", "[out]"]
    cmd += NVENC_H265_ARGS + [str(output)]
    _run(cmd)
    return output
