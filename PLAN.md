# PLAN.md — Full Pipeline: Static PNG → Animated Wallpaper

## Architecture

Two independent projects + one orchestration script:

```
┌─────────────────────────────────────────────────────────────┐
│                    orchestrate.py                            │
│         (thin script that chains the two tools)             │
├──────────────────────────┬──────────────────────────────────┤
│    animate/              │         convert/                  │
│    (AI animation)        │         (media processing)       │
│                          │                                  │
│  PNG ──→ raw MP4 clip    │  raw MP4 ──→ upscale ──→ GIF    │
│                          │          ──→ loop ──→ WebP       │
│  FramePack               │          ──→ 4K MP4              │
│  Wan 2.2 (ComfyUI)      │          ──→ wallpaper-ready     │
│  LivePortrait            │                                  │
│                          │  FFmpeg, Gifski, Real-ESRGAN,    │
│  PyTorch + CUDA          │  gifsicle, ImageMagick           │
└──────────────────────────┴──────────────────────────────────┘
```

**Key architectural rule:** convert knows nothing about AI models. animate knows nothing about GIF encoding. The orchestrator is ~80 lines of subprocess calls.

## Implementation Order

### Phase 1: convert core (week 1)
1. `config.py` + `convert check` — verify all binaries present
2. `core/ffmpeg.py` — all FFmpeg wrappers + tests
3. `converters/to_gif.py` + `converters/to_mp4.py`
4. `upscale/realesrgan.py` + `core/pipeline.py`
5. `upscale_then_gif` and `upscale_then_mp4` pipelines
6. `make_seamless_loop` — crossfade looping
7. `animate_to_4k_wallpaper` pipeline preset
8. CLI with Typer — `convert`, `upscale`, `upscale-gif`, `optimize`

### Phase 2: animate (week 2)
1. Install FramePack backend, verify it runs
2. Write `run_framepack.py` wrapper
3. Write prompt templates for ambient animation
4. Test end-to-end: PNG → FramePack → raw MP4
5. Install ComfyUI + Wan 2.2 weights, verify
6. Write `run_wan22.py` wrapper (calls ComfyUI API)
7. Install LivePortrait, write `run_liveportrait.py`
8. Wire up `orchestrate.py`

### Phase 3: convert remaining features (week 3)
1. Remaining converters (webp, apng, avif, jxl, etc.)
2. `tools/` — optimize, transform, effects, frames
3. Web UI (FastAPI + HTMX)
4. Bulk operations
5. Tests

### Phase 4: polish (week 4)
1. Batch mode for animate (multiple seeds/prompts)
2. A/B comparison view in web UI
3. Wallpaper Engine workshop upload helper
4. README + docs

## Hardware Utilization

| Component | Used By |
|---|---|
| RTX 5090 (CUDA) | FramePack, Wan 2.2, LivePortrait (PyTorch) |
| RTX 5090 (Vulkan) | Real-ESRGAN ncnn, waifu2x ncnn |
| RTX 5090 (NVENC) | FFmpeg H.264/H.265 encoding (-c:v hevc_nvenc) |
| RTX 5090 (NVDEC) | FFmpeg hardware decode (-hwaccel cuda) |
| 7800X3D (CPU) | Gifski encoding, gifsicle, ImageMagick, general |
| 64GB DDR5 | Large frame buffers, no swap pressure during 4K upscale |

## 4K Upscaling Performance Estimates (RTX 5090)

| Input | Scale | Output | Model | Est. Time |
|---|---|---|---|---|
| 720p, 150 frames (5s@30fps) | 4x | 2880p | animevideov3 | ~2-5 min |
| 720p, 150 frames | 2x | 1440p | animevideov3 | ~1-2 min |
| 480p, 150 frames | 4x | 1920p | animevideov3 | ~1-3 min |
| 1080p, 150 frames | 4x | 4320p (crop to 4K) | animevideov3 | ~5-15 min |
| 1080p, 900 frames (30s@30fps) | 2x | 2160p | animevideov3 | ~5-10 min |

## GIF Size Reality Check at 4K

| Resolution | FPS | Duration | Colors | Approx Size |
|---|---|---|---|---|
| 3840×2160 | 15 | 3s | 256 | 80-200 MB |
| 3840×2160 | 15 | 5s | 256 | 130-350 MB |
| 1920×1080 | 15 | 5s | 256 | 30-80 MB |
| 1280×720 | 15 | 5s | 256 | 10-30 MB |

**Use MP4 (H.265) for 4K animated wallpapers.** Reserve GIF for ≤1080p short loops for sharing (Discord, forums).

## Output Format by Use Case

| Use Case | Format | Why |
|---|---|---|
| Wallpaper Engine | MP4 (H.265, CRF 18) | Small file, full color, hardware decoded |
| Lively Wallpaper | MP4 or GIF | Accepts both |
| Discord/forum avatar | GIF ≤256px wide, ≤10MB | Platform limits |
| Discord embed | GIF ≤1080p, <50MB | Larger but auto-plays |
| Twitter/X post | MP4 ≤1080p | Re-encoded anyway |
| Phone wallpaper | MP4 or live photo | Depends on OS |
| Web/sharing | WebP animated | Best size/quality ratio |
| Archival/lossless | APNG or lossless WebP | Full color, large |
