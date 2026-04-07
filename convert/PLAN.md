# convert — Implementation Plan

## Goal

Full ezgif.com replacement that runs locally with GPU-accelerated upscaling.
General-purpose — works on any video/GIF input, not anime-specific.
Outputs wallpaper-ready 4K MP4 when used in the wallpaper pipeline.

## Core Design Principles

- Each module does one thing and wraps one binary or one concern
- `core/pipeline.py` chains modules — no business logic in CLI or converters
- All paths configurable in `config.py` — no hardcoded binary locations
- Fail fast with helpful error messages when binaries are missing (`convert check`)
- Never write temp files to the input directory — always to a controlled temp dir

## config.py

```python
from pathlib import Path
import shutil

BASE = Path(__file__).parent
BIN = BASE / "bin"

# Binary resolution: bin/ first, then PATH
def _find(name: str) -> Path:
    p = BIN / f"{name}.exe"
    if p.exists():
        return p
    found = shutil.which(name)
    if found:
        return Path(found)
    raise FileNotFoundError(f"{name} not found in bin/ or PATH")

FFMPEG        = _find("ffmpeg")
FFPROBE       = _find("ffprobe")
GIFSKI        = _find("gifski")
GIFSICLE      = _find("gifsicle")
REALESRGAN    = _find("realesrgan-ncnn-vulkan")
IMAGEMAGICK   = _find("magick")

# Optional — set path if waifu2x installed locally
WAIFU2X: Path | None = None  # e.g. Path(r"C:\tools\waifu2x-ncnn-vulkan.exe")

# Defaults
DEFAULT_FPS         = 15
DEFAULT_SCALE       = 2
DEFAULT_GIF_COLORS  = 256
DEFAULT_REALESRGAN_MODEL = "realesr-animevideov3"
TEMP_DIR            = BASE / ".tmp"
```

## Module Specs

### core/ffmpeg.py

All FFmpeg subprocess calls. Returns `Path` to output file. Raises on
non-zero exit code with ffmpeg's stderr included in the exception.

```python
def extract_frames(input: Path, output_dir: Path, fps: float = None) -> list[Path]
def frames_to_video(frames_dir: Path, output: Path, fps: float, nvenc: bool = True) -> Path
def video_to_video(input: Path, output: Path, fps: float = None, width: int = None,
                   crf: int = 18, nvenc: bool = True) -> Path
def get_video_info(input: Path) -> dict  # fps, width, height, duration, frame_count
def pad_or_crop(input: Path, output: Path, width: int, height: int) -> Path
def crossfade_loop(input: Path, output: Path, crossfade_frames: int = 15) -> Path
```

### upscale/realesrgan.py

```python
def upscale_frames(
    input_dir: Path,   # directory of PNG frames
    output_dir: Path,
    scale: int = 4,
    model: str = "realesr-animevideov3",
    gpu_id: int = 0,
) -> list[Path]

def upscale_image(input: Path, output: Path, scale: int = 4, model: str = "realesrgan-x4plus-anime") -> Path
```

Calls `realesrgan-ncnn-vulkan.exe -i {input_dir} -o {output_dir} -n {model} -s {scale} -g {gpu_id}`.
Uses Vulkan — doesn't touch CUDA, so can run alongside NVENC simultaneously.

### upscale/waifu2x.py

Same interface as realesrgan.py — drop-in alternative.

### converters/to_gif.py

```python
def frames_to_gif(
    frames: list[Path],
    output: Path,
    fps: float = 15,
    width: int = None,      # None = preserve
    colors: int = 256,
    lossy: int = None,      # None = lossless gifski, int = gifsicle lossy
    optimize_level: int = 3,
) -> Path
```

Step 1: gifski for high-quality palette + dithering
Step 2: gifsicle for optimization + lossy if requested

### converters/to_mp4.py

```python
def frames_to_mp4(frames: list[Path], output: Path, fps: float, nvenc: bool = True) -> Path
def gif_to_mp4(input: Path, output: Path, fps: float = None, nvenc: bool = True) -> Path
```

### tools/loop.py

```python
def make_seamless_loop(input: Path, output: Path, crossfade_frames: int = 15) -> Path
```

1. Extract all frames
2. Blend last N frames linearly into first N frames
3. Drop last N frames
4. Reassemble

### core/pipeline.py — Key Pipelines

```python
def upscale_then_gif(input: Path, output: Path, scale: int, fps: float,
                     width: int = None, lossy: int = None) -> Path
    """MP4/GIF → upscale frames → reassemble → gifski → gifsicle"""

def upscale_then_mp4(input: Path, output: Path, scale: int, fps: float = None,
                     crf: int = 18) -> Path
    """MP4 → upscale frames → NVENC encode"""

def animate_to_4k_wallpaper(
    input: Path,
    output: Path,
    target_width: int = 3840,
    target_height: int = 2160,
    scale: int = 4,
    model: str = "realesr-animevideov3",
    output_format: str = "mp4",
    fps: float = None,
    loop: bool = True,
    crossfade_frames: int = 15,
) -> Path:
    """
    Full pipeline: raw animation clip → 4K wallpaper-ready output
    1. Extract frames
    2. Upscale all frames via Real-ESRGAN
    3. Pad/crop to exact target resolution
    4. If loop: crossfade last/first frames
    5. Encode to output format
    """
```

## CLI Commands (Typer)

```bash
convert check                        # verify all binaries, print versions
convert convert INPUT OUTPUT          # generic convert (auto-detect format)
convert upscale INPUT OUTPUT          # upscale image or video
convert upscale-gif INPUT OUTPUT      # upscale then encode as GIF
convert optimize INPUT OUTPUT         # optimize GIF size
convert loop INPUT OUTPUT             # make seamless loop
convert pipeline wallpaper IN OUT     # 4K wallpaper preset
convert serve                         # start web UI
convert info INPUT                    # print video metadata
```

## Web UI (FastAPI + HTMX)

- Port 8765 by default
- Drag-and-drop file upload
- Select operation (convert, upscale, optimize, loop, pipeline)
- Live progress updates via SSE or polling
- Download result
- No JS framework — HTMX only, renders server-side

## Implementation Order

1. `config.py` — paths + binary resolution
2. `convert check` command — verify binaries, print versions
3. `core/ffmpeg.py` — wrappers + basic tests
4. `upscale/realesrgan.py` — frame upscaling
5. `converters/to_gif.py` — gifski + gifsicle
6. `converters/to_mp4.py` — NVENC encode
7. `core/pipeline.py` — `upscale_then_gif`, `upscale_then_mp4`
8. `tools/loop.py` — crossfade seamless loop
9. `core/pipeline.py` — `animate_to_4k_wallpaper`
10. CLI — all commands with Typer
11. Remaining converters — webp, apng
12. `tools/` — optimize, effects, frames
13. Web UI — FastAPI + HTMX
14. `upscale/waifu2x.py` — wire in existing waifu2x install
15. Tests

## Temp File Strategy

All intermediate files go to `convert/.tmp/{job_id}/`.
Cleaned up automatically on success. Preserved on failure for debugging.
`convert clean` removes all temp dirs.
