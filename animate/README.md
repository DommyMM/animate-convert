# animate

Takes a static PNG illustration and produces a short ambient animation
(hair sway, blinking, breathing, ribbon flutter) that preserves the original
art style. Outputs raw MP4 → hand off to convert for upscaling and encoding.

## Backends

| Backend | Model | VRAM | Speed (RTX 5090) | Best For |
|---|---|---|---|---|
| **FramePack** (primary) | HunyuanVideo 13B | ~12GB | ~0.8-1.2s/frame → 5s clip in <1 min | Quick iterations, testing prompts |
| **Wan 2.2 14B** (quality) | Wan 2.2 I2V 14B via ComfyUI | ~20GB | ~30-50 min / 2.3s clip at 720p | Final quality output |
| **Wan 2.2 5B** (fast) | Wan 2.2 I2V 5B via ComfyUI | ~12GB | ~5-10 min / 2.3s clip | Quality + speed balance |
| **LivePortrait** (face) | LivePortrait | near real-time | near real-time | Face-only: blink, gaze, head |

FramePack auto-downloads ~30GB of weights on first run.

## Directory Structure

```
animate/
├── run_framepack.py          # CLI wrapper for FramePack
├── run_wan22.py              # CLI wrapper for Wan 2.2 ComfyUI API
├── run_liveportrait.py       # CLI wrapper for LivePortrait
├── config.py                 # Paths to each backend install
├── requirements.txt
├── backends/                 # Git clones live here
│   ├── framepack/
│   ├── liveportrait/
│   └── (comfyui installed separately)
├── output/                   # Raw MP4s land here
└── README.md
```

## CLI

```bash
# FramePack (quick iteration)
py run_framepack.py input.png output.mp4 \
  --prompt "silver hair swaying gently in breeze, ribbons flutter, slow blink" \
  --seconds 5 \
  --seed 42

# Wan 2.2 (highest quality)
py run_wan22.py input.png output.mp4 \
  --prompt "gentle wind blowing hair, subtle breathing" \
  --model 14b \
  --steps 30

# LivePortrait (face animation only)
py run_liveportrait.py input.png output.mp4 \
  --driving webcam          # or --driving reference.mp4

# Batch: try multiple seeds, pick the best
py run_framepack.py input.png ./output/ \
  --prompt "hair swaying gently" \
  --seeds 42,123,456,789 \
  --seconds 3
```

## Setup

### FramePack (start here)

```bash
cd backends
git clone https://github.com/lllyasviel/FramePack.git framepack
cd framepack
py -m venv venv
venv\Scripts\activate.bat
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
pip install sageattention==1.0.6
# First run downloads ~30GB of HunyuanVideo weights automatically
```

### Wan 2.2 via ComfyUI

```bash
# Install ComfyUI separately per its own instructions
# Download Wan 2.2 I2V weights to ComfyUI's models/ directory
# animate calls ComfyUI's REST API endpoint
# Set COMFYUI_URL in config.py (default: http://127.0.0.1:8188)
```

### LivePortrait

```bash
cd backends
git clone https://github.com/KwaiVGI/LivePortrait.git liveportrait
cd liveportrait
py -m venv venv
venv\Scripts\activate.bat
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

## Prompt Tips

**Good — subtle ambient motion:**
```
silver hair swaying gently in a light breeze, ribbons fluttering softly
gentle breathing motion, slow deliberate blink, serene expression
flower petals drifting slowly past, hair strands catching the wind
```

**Bad — too much motion, will distort the image:**
```
dancing, running, jumping, turning around
dramatic wind, storm, hair whipping violently
talking, laughing, crying
```

Keep it **minimal and environmental**. These models preserve source art best
when asked for subtle effects, not character actions.

## Implementation Notes

- Each backend lives in its own venv under `backends/` to isolate deps
- `run_*.py` scripts activate the correct venv and call the backend
- Output is always raw MP4 at native resolution — convert handles upscaling
- Seed is always saved in the output filename: `output_seed42.mp4`
- FramePack wrapper calls its Gradio API or imports directly

## Acknowledgments

- [FramePack](https://github.com/lllyasviel/FramePack) by lllyasviel
- [Wan 2.2](https://github.com/Wan-Video/Wan2.2) by Alibaba
- [LivePortrait](https://github.com/KwaiVGI/LivePortrait) by Kuaishou
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
