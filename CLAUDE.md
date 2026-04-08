# Project Context for AI Agents

This is a personal tool for animating static anime illustrations into 4K wallpapers, running entirely locally.

## Architecture

Two independent Python projects plus a thin orchestrator:

```
root/
├── animate/        PNG → raw MP4 via AI animation backends
├── convert/        raw MP4 → upscaled/encoded final output
├── orchestrate.py  chains the two projects via subprocess
├── input/          drop PNGs here
└── output/         final wallpapers land here
```

They are kept separate because `animate/` needs 30-60GB of PyTorch models and a fragile CUDA dep matrix, while `convert/` needs only CLI binaries (~50MB). Combining them would mean every media conversion task drags in AI weights. The orchestrator is the only coupling between them.

## Hardware Context

- RTX 5090 32GB — FramePack, Wan 2.2, Real-ESRGAN (Vulkan), NVENC encode/decode
- 7800X3D — gifski, gifsicle, ImageMagick, general CPU work
- 64GB DDR5 — no swap pressure during 4K frame processing

Target output resolution: 4K (3840×2160). Lower is acceptable. Wallpaper Engine / Lively Wallpaper as the delivery target (accept MP4 directly). GIF only for ≤1080p sharing (Discord etc.) — 4K GIF is absurdly large.

## Tooling

- **Python**: `py` command (Windows). Both subprojects use `uv` for dependency management.
- **Shell**: bash (Git Bash on Windows). Use forward slashes and Unix syntax.
- **No dev servers** unless explicitly asked.
- `convert/` uses uv with `pyproject.toml`. Run `uv run` or activate `.venv`.
- `animate/` uses uv for its own wrapper scripts. Each AI backend (`backends/framepack/`, `backends/liveportrait/`) has its own venv managed separately — never mix these with the top-level project env.

## convert/ — Media Processing

**Purpose:** General-purpose media conversion and processing. Not anime-specific. An ezgif.com replacement with GPU upscaling.

**External binaries** (in `convert/bin/` or system PATH):
- `ffmpeg` / `ffprobe` — already installed system-wide
- `magick` (ImageMagick) — already installed system-wide
- `realesrgan-ncnn-vulkan.exe` — in `convert/bin/`, models in `convert/bin/models/`
- `gifski.exe` — CLI installed via cargo to `C:\Users\domin\.cargo\bin\gifski.exe` (v1.34.0). The winget gifski is a GUI app — ignore it.
- `gifsicle.exe` — installed via choco to `C:\ProgramData\chocolatey\lib\gifsicle\tools\gifsicle.exe`

**Python deps:** typer, fastapi, uvicorn, rich, pytest (dev)

**Key modules to implement (in order):**
1. `config.py` — binary resolution (bin/ first, then PATH), defaults
2. `core/ffmpeg.py` — all FFmpeg subprocess wrappers
3. `upscale/realesrgan.py` — frame upscaling via ncnn-vulkan
4. `converters/to_gif.py` — gifski + gifsicle pipeline
5. `converters/to_mp4.py` — NVENC H.265 encode
6. `core/pipeline.py` — `upscale_then_gif`, `upscale_then_mp4`, `animate_to_4k_wallpaper`
7. `tools/loop.py` — seamless crossfade loop
8. `main.py` — Typer CLI
9. `server.py` — FastAPI + HTMX web UI

**FFmpeg NVENC flags for RTX 5090:**
```python
NVENC_H265_ARGS = ["-c:v", "hevc_nvenc", "-preset", "p7", "-tune", "hq",
                   "-rc", "constqp", "-qp", "18", "-b:v", "0", "-profile:v", "main10"]
HWACCEL_DECODE_ARGS = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
```

Real-ESRGAN uses Vulkan compute; FFmpeg uses CUDA video engine — different hardware units, no contention.

## animate/ — AI Animation

**Purpose:** Wrap AI video generation backends behind a consistent CLI. Takes a PNG, outputs a raw MP4 clip.

**Backends (each in `backends/<name>/` with its own venv):**
- `framepack` — HunyuanVideo 13B, ~12GB VRAM, ~2-3 min for 5s clip. Primary for iteration.
- `wan` — Wan 2.2 I2V via ComfyUI REST API, ~20GB VRAM, ~30-50 min/2.3s. Best quality.
- `face` — LivePortrait, near real-time, face-only animation.

**Wrapper scripts:** `run_framepack.py`, `run_wan22.py`, `run_liveportrait.py`
Each activates its own backend venv and calls inference. Output is always raw MP4 at native resolution.

**Not yet implemented** — backends need to be cloned and set up separately when ready to test.

## orchestrate.py

Stdlib only. Calls `animate/run_<backend>.py` then `convert/` CLI via subprocess. ~80 lines. See the file for full CLI.

## Current State

- [x] Project scaffold committed
- [x] `convert/` uv project initialized (pyproject.toml, .venv)
- [x] `animate/` uv project initialized
- [x] Real-ESRGAN ncnn-vulkan extracted to `convert/bin/` with all models
- [x] gifski CLI installed via cargo (`C:\Users\domin\.cargo\bin\gifski.exe` v1.34.0)
- [x] gifsicle installed via choco (v1.95)
- [x] ffmpeg installed system-wide
- [x] ImageMagick installed system-wide
- [ ] `convert/` core modules not yet written
- [ ] `animate/` backends not yet cloned/set up

## What NOT to do

- Don't commit `.venv/`, `backends/`, `*.safetensors`, `*.bin`, `*.param`, `input/`, `output/` — all gitignored
- Don't mix animate backend deps into the top-level animate/ venv
- Don't use `python` or `python3` — use `py` on this system
- Don't start dev servers without being asked
