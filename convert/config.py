"""
Binary resolution and project-wide defaults.

Priority order: convert/bin/ → system PATH.
"""
import shutil
from pathlib import Path

BASE = Path(__file__).parent
BIN = BASE / "bin"


def _find(name: str, *, required: bool = True) -> Path | None:
    """Resolve a binary: bin/ first, then PATH."""
    candidate = BIN / f"{name}.exe"
    if candidate.exists():
        return candidate
    found = shutil.which(name)
    if found:
        return Path(found)
    if required:
        raise FileNotFoundError(
            f"'{name}' not found in {BIN}/ or system PATH. "
            f"See convert/CLAUDE.md for install instructions."
        )
    return None


FFMPEG    = _find("ffmpeg")
FFPROBE   = _find("ffprobe")
MAGICK    = _find("magick")
GIFSKI    = _find("gifski")
GIFSICLE  = _find("gifsicle")
REALESRGAN = _find("realesrgan-ncnn-vulkan")

# waifu2x — in bin/waifu2x/ subdirectory
_waifu2x_candidate = BIN / "waifu2x" / "waifu2x-ncnn-vulkan.exe"
WAIFU2X: Path | None = _waifu2x_candidate if _waifu2x_candidate.exists() else _find("waifu2x-ncnn-vulkan", required=False)

# Real-ESRGAN models directory (next to the exe in bin/)
REALESRGAN_MODELS = REALESRGAN.parent / "models" if REALESRGAN else None

# Defaults
DEFAULT_FPS             = 15
DEFAULT_REALESRGAN_MODEL = "realesr-animevideov3"
DEFAULT_CROSSFADE_FRAMES = 15

# Temp dir — cleaned on success, preserved on failure for debugging
TEMP_DIR = BASE / ".tmp"

NVENC_H265_ARGS = [
    "-c:v", "hevc_nvenc",
    "-preset", "p7",
    "-tune", "hq",
    "-rc", "constqp",
    "-qp", "18",
    "-b:v", "0",
    "-profile:v", "main10",
]

HWACCEL_DECODE_ARGS = [
    "-hwaccel", "cuda",
    "-hwaccel_output_format", "cuda",
]
