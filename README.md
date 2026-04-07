# wallforge

Turn a static anime illustration into an ambient animated 4K wallpaper, entirely locally.

```
static PNG → AI animation → upscale to 4K → seamless loop → wallpaper
```

## Structure

```
wallforge/
├── animate/              # AI animation: PNG → raw MP4
├── convert/              # Media processing: raw MP4 → final output
├── orchestrate.py        # Chains both tools together
├── input/                # Drop your PNGs here
└── output/               # Final wallpapers land here
```

## Quick Start

```bash
# Full pipeline
python orchestrate.py \
  --input input/gacha_girl.png \
  --output output/ \
  --backend framepack \
  --prompt "silver hair swaying gently in breeze, ribbons flutter softly, subtle breathing, slow blink" \
  --seconds 5 \
  --seed 42 \
  --upscale 4 \
  --format mp4 \
  --resolution 4k \
  --loop

# Skip animation (already have a clip)
python orchestrate.py \
  --input input/existing_clip.mp4 \
  --output output/ \
  --skip-animate \
  --upscale 2 \
  --format gif \
  --resolution 1080p \
  --loop

# Animate only
python orchestrate.py \
  --input input/gacha_girl.png \
  --output output/ \
  --backend framepack \
  --prompt "hair blowing" \
  --skip-postprocess
```

## Output Formats

| Goal | Format | Flag |
|---|---|---|
| Desktop wallpaper | MP4 H.265 | `--format mp4` |
| Discord avatar (≤10MB) | GIF | `--format gif --resolution 720p` |
| Web sharing | WebP animated | `--format webp` |
| Archive | APNG | `--format apng` |

For 4K always use MP4 — GIF at 4K is 80-350MB and capped at 256 colors. Wallpaper Engine and Lively both accept MP4 directly.

## Docs

- [animate/README.md](animate/README.md) — AI animation backends (FramePack, Wan 2.2, LivePortrait)
- [convert/README.md](convert/README.md) — Media processing (FFmpeg, Real-ESRGAN, gifski)
- [PLAN.md](PLAN.md) — Full architecture and implementation order
