# convert

Local CLI + web UI for media conversion and processing. A full
ezgif.com replacement with GPU-accelerated upscaling via Real-ESRGAN.
General purpose — not anime-specific.

## What It Does

- Convert video ↔ GIF ↔ WebP ↔ APNG ↔ MP4
- Upscale frames via Real-ESRGAN (Vulkan, uses your GPU) or waifu2x
- Create seamless loops via crossfade blending
- Optimize GIFs (gifsicle, lossy compression)
- Encode final MP4 via NVENC (hevc_nvenc) on your RTX 5090
- Full 4K pipeline preset for animated wallpapers

## CLI

```bash
# Convert video to high-quality GIF
py -m convert convert video.mp4 output.gif --fps 15 --width 640

# Upscale then GIF
py -m convert upscale-gif video.mp4 output.gif --scale 2 --fps 15

# Upscale image or video
py -m convert upscale photo.jpg photo_4x.jpg --scale 4
py -m convert upscale clip.mp4 clip_4x.mp4 --scale 4 --model animevideov3

# Optimize GIF
py -m convert optimize big.gif small.gif --level 3 --lossy 80

# Full wallpaper pipeline preset
py -m convert pipeline wallpaper raw_clip.mp4 output.mp4 \
    --scale 4 --format mp4 --width 3840 --height 2160 --loop

# Start web UI
py -m convert serve
# → http://127.0.0.1:8765
```

## Directory Structure

```
convert/
├── __main__.py           # Entry point: py -m convert
├── main.py               # Typer CLI definitions
├── server.py             # FastAPI + HTMX web UI
├── config.py             # Binary paths, defaults
├── core/
│   ├── ffmpeg.py         # All FFmpeg subprocess wrappers
│   └── pipeline.py       # High-level pipelines (upscale_then_gif, etc.)
├── converters/
│   ├── to_gif.py         # Video/frames → GIF (gifski + gifsicle)
│   ├── to_mp4.py         # GIF/frames → MP4 (NVENC)
│   ├── to_webp.py        # → animated WebP
│   └── to_apng.py        # → APNG
├── upscale/
│   ├── realesrgan.py     # Real-ESRGAN ncnn-vulkan wrapper
│   └── waifu2x.py        # waifu2x ncnn-vulkan wrapper
├── tools/
│   ├── optimize.py       # GIF optimization (gifsicle)
│   ├── loop.py           # Seamless loop / crossfade
│   ├── frames.py         # Extract / reassemble frames
│   └── effects.py        # Crop, resize, rotate, speed
├── bin/                  # Place binary EXEs here
│   ├── realesrgan-ncnn-vulkan.exe
│   ├── gifski.exe
│   ├── gifsicle.exe
│   └── waifu2x-ncnn-vulkan.exe  (optional, you have local install)
├── requirements.txt
└── README.md
```

## Setup

### 1. System binaries

```bash
winget install Gyan.FFmpeg
# gifski + gifsicle: place in bin/ or on PATH
# Download from:
#   https://gif.ski/ (gifski)
#   http://www.lcdf.org/gifsicle/ (gifsicle)
winget install ImageMagick.ImageMagick
```

### 2. Real-ESRGAN

Download `realesrgan-ncnn-vulkan` from:
https://github.com/xinntao/Real-ESRGAN/releases

Place `realesrgan-ncnn-vulkan.exe` and the `models/` folder in `bin/`.

Key models for anime:
- `realesr-animevideov3` — anime video frames (use this for wallpapers)
- `realesrgan-x4plus-anime` — anime images
- `realesrgan-x4plus` — general photos

### 3. Python environment

```bash
cd convert
py -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt

# Verify all binaries found
py -m convert check
```

### 4. waifu2x (optional)

You have waifu2x locally. Set its path in `config.py`:
```python
WAIFU2X_PATH = Path(r"C:\path\to\waifu2x-ncnn-vulkan.exe")
```

## Pipeline Presets

### `animate_to_4k_wallpaper`

```
Input: raw MP4 from animate (720p or 1080p)
Steps:
  1. Extract frames
  2. Upscale all frames 4x via Real-ESRGAN (animevideov3)
  3. Pad/crop to exact 3840×2160
  4. Create seamless loop (crossfade first/last N frames)
  5. Encode to H.265 MP4 via NVENC
Output: 4K MP4, ready for Wallpaper Engine
```

### `make_seamless_loop`

```
Input: any clip
Steps:
  1. Extract all frames
  2. Crossfade last N frames back into first N frames
  3. Trim last N frames
  4. Reassemble
Output: seamlessly looping clip
```

## FFmpeg NVENC Flags (RTX 5090)

```python
# hevc_nvenc — offloads encode entirely to GPU
# Frees CPU for gifski/gifsicle/ImageMagick during pipeline
NVENC_H265_ARGS = [
    "-c:v", "hevc_nvenc",
    "-preset", "p7",        # slowest/best quality NVENC preset
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
```

CUDA decode + Vulkan compute (Real-ESRGAN) run simultaneously — different
hardware units on the 5090. No contention during upscale pipeline.

## Acknowledgments

- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) by Xintao
- [Gifski](https://gif.ski/) by Kornel Lesiński
- [FFmpeg](https://ffmpeg.org/)
- [gifsicle](http://www.lcdf.org/gifsicle/)
