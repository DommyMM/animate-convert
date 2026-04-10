"""
waifu2x ncnn-vulkan wrapper.

Uses Vulkan compute — same as Real-ESRGAN, no CUDA contention.

Models:
  models-cunet                         — best quality (default for anime)
  models-upconv_7_anime_style_art_rgb  — faster, good for anime
  models-upconv_7_photo                — for photos

Noise levels:
  -1  no denoise
   0  low denoise
   1  medium denoise
   2  high denoise
   3  highest denoise
"""
import subprocess
from pathlib import Path

from convert.config import WAIFU2X


def _waifu2x_models_dir() -> Path:
    """Get models directory relative to the waifu2x exe."""
    return WAIFU2X.parent


def upscale_frames(
    input_dir: Path,
    output_dir: Path,
    scale: int = 2,
    noise: int = -1,
    model: str = "models-cunet",
    gpu_id: int = 0,
) -> list[Path]:
    """
    Upscale all images in input_dir via waifu2x, write to output_dir.

    waifu2x only supports 2x scale. For 4x, run twice.
    """
    if WAIFU2X is None:
        raise FileNotFoundError("waifu2x-ncnn-vulkan not found. See config.py.")

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = _waifu2x_models_dir() / model

    cmd = [
        str(WAIFU2X),
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-n", str(noise),
        "-s", str(scale),
        "-m", str(model_path),
        "-g", str(gpu_id),
        "-f", "png",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"waifu2x failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )
    return sorted(output_dir.glob("*.png"))


def upscale_image(
    input: Path,
    output: Path,
    scale: int = 2,
    noise: int = -1,
    model: str = "models-cunet",
    gpu_id: int = 0,
) -> Path:
    """Upscale a single image via waifu2x."""
    if WAIFU2X is None:
        raise FileNotFoundError("waifu2x-ncnn-vulkan not found. See config.py.")

    output.parent.mkdir(parents=True, exist_ok=True)
    model_path = _waifu2x_models_dir() / model

    cmd = [
        str(WAIFU2X),
        "-i", str(input),
        "-o", str(output),
        "-n", str(noise),
        "-s", str(scale),
        "-m", str(model_path),
        "-g", str(gpu_id),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"waifu2x failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )
    return output
