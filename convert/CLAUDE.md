# convert/ — Agent Context

Media processing subproject. General-purpose, not anime-specific. See root [CLAUDE.md](../CLAUDE.md) for full project context.

## What This Does

Receives raw MP4 (from `animate/` or any source) and produces final output: upscaled GIF, WebP, APNG, or H.265 MP4. Also works standalone as a local ezgif.com replacement.

## Stack

- `uv` for deps. Run with `uv run python -m convert` or activate `.venv`.
- Typer for CLI, FastAPI + HTMX for web UI, Rich for terminal output.
- All heavy lifting done by external binaries — no PyTorch, no CUDA Python deps.

## External Binaries

| Binary | Location | Status |
|---|---|---|
| `ffmpeg` / `ffprobe` | system PATH | installed |
| `magick` (ImageMagick) | system PATH | installed |
| `realesrgan-ncnn-vulkan.exe` | `bin/` | installed + models |
| `gifski.exe` | `C:\Users\domin\.cargo\bin\` (cargo CLI, v1.34.0) | installed |
| `gifsicle.exe` | system PATH (choco, v1.95) | installed |

`config.py` resolves binaries by checking `bin/` first, then PATH. Set `GIFSKI_PATH` override if needed.

## Module Build Order

Implement in this order — each depends on the previous:

1. `config.py` — binary resolution, paths, defaults
2. `core/ffmpeg.py` — FFmpeg subprocess wrappers (extract_frames, frames_to_video, get_video_info, pad_or_crop)
3. `upscale/realesrgan.py` — `upscale_frames(input_dir, output_dir, scale, model)` using Vulkan
4. `converters/to_gif.py` — gifski encode → gifsicle optimize
5. `converters/to_mp4.py` — NVENC H.265 encode
6. `core/pipeline.py` — `upscale_then_gif`, `upscale_then_mp4`, `animate_to_4k_wallpaper`, `make_seamless_loop`
7. `tools/loop.py` — crossfade loop helper
8. `main.py` — Typer CLI (`convert`, `upscale`, `upscale-gif`, `optimize`, `loop`, `pipeline`, `serve`, `check`)
9. `server.py` — FastAPI + HTMX web UI on port 8765

## Key Implementation Details

**Real-ESRGAN call pattern:**
```python
# Vulkan — doesn't touch CUDA, runs alongside NVENC simultaneously
cmd = [str(REALESRGAN), "-i", str(input_dir), "-o", str(output_dir),
       "-n", model, "-s", str(scale), "-g", "0"]
```

**NVENC encode for RTX 5090:**
```python
NVENC_H265 = ["-c:v", "hevc_nvenc", "-preset", "p7", "-tune", "hq",
              "-rc", "constqp", "-qp", "18", "-b:v", "0", "-profile:v", "main10"]
HWACCEL_IN = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
```

**Temp files:** always to `.tmp/{job_id}/`, cleaned on success, preserved on failure.

**GIF pipeline:** gifski (quality palette + dithering) → gifsicle (size optimization + optional lossy). Never call gifsicle without gifski first.

**4K note:** For 4K output always use MP4 H.265. GIF at 3840×2160 is 80-350MB and 256 colors. Wallpaper Engine and Lively Wallpaper accept MP4 directly.
