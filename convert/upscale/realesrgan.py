"""
Real-ESRGAN ncnn-vulkan wrapper.

Uses Vulkan compute — entirely separate from CUDA, so it can run
simultaneously with NVENC encoding with no contention on the RTX 5090.
"""
import subprocess
from pathlib import Path

from convert.config import REALESRGAN, REALESRGAN_MODELS, DEFAULT_REALESRGAN_MODEL


def upscale_frames(
    input_dir: Path,
    output_dir: Path,
    scale: int = 4,
    model: str = DEFAULT_REALESRGAN_MODEL,
    gpu_id: int = 0,
) -> list[Path]:
    """
    Upscale all PNG frames in input_dir, write results to output_dir.

    Model options:
      realesr-animevideov3   — anime video frames (default, best for wallpapers)
      realesrgan-x4plus-anime — anime still images
      realesrgan-x4plus       — general photos
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(REALESRGAN),
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-n", model,
        "-s", str(scale),
        "-g", str(gpu_id),
        "-f", "png",
    ]
    if REALESRGAN_MODELS:
        cmd += ["-m", str(REALESRGAN_MODELS)]

    result = subprocess.run(
        cmd, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"realesrgan-ncnn-vulkan failed (exit {result.returncode}):\n"
            f"{result.stderr[-2000:]}"
        )
    return sorted(output_dir.glob("*.png"))


def upscale_image(
    input: Path,
    output: Path,
    scale: int = 4,
    model: str = "realesrgan-x4plus-anime",
    gpu_id: int = 0,
) -> Path:
    """Upscale a single image file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(REALESRGAN),
        "-i", str(input),
        "-o", str(output),
        "-n", model,
        "-s", str(scale),
        "-g", str(gpu_id),
    ]
    if REALESRGAN_MODELS:
        cmd += ["-m", str(REALESRGAN_MODELS)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"realesrgan-ncnn-vulkan failed (exit {result.returncode}):\n"
            f"{result.stderr[-2000:]}"
        )
    return output
