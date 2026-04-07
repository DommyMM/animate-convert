# animate — Implementation Plan

## Goal

Wrap three AI animation backends (FramePack, Wan 2.2, LivePortrait) behind
a consistent CLI so orchestrate.py can call any of them without caring about
their internal APIs, venv locations, or model loading details.

## Architecture

```
animate/
├── run_framepack.py      # Entry point: activate venv, call FramePack
├── run_wan22.py          # Entry point: call ComfyUI REST API
├── run_liveportrait.py   # Entry point: activate venv, call LivePortrait
├── config.py             # All paths and settings
├── requirements.txt      # Only stdlib + requests (for ComfyUI API calls)
└── backends/             # Git clones, each with own venv
    ├── framepack/
    └── liveportrait/
```

## config.py

```python
from pathlib import Path

BASE = Path(__file__).parent
BACKENDS = BASE / "backends"

FRAMEPACK_DIR = BACKENDS / "framepack"
FRAMEPACK_VENV = FRAMEPACK_DIR / "venv"

LIVEPORTRAIT_DIR = BACKENDS / "liveportrait"
LIVEPORTRAIT_VENV = LIVEPORTRAIT_DIR / "venv"

COMFYUI_URL = "http://127.0.0.1:8188"   # Edit if ComfyUI runs elsewhere
COMFYUI_WAN22_WORKFLOW = BASE / "workflows" / "wan22_i2v.json"

OUTPUT_DIR = BASE / "output"
```

## run_framepack.py — Spec

**Inputs:**
- `input_png`: Path — source image
- `output`: Path — output file or directory
- `--prompt`: str — animation description
- `--seconds`: int (default 5)
- `--seed`: int (default None → random)
- `--seeds`: str — comma-separated list for batch mode (e.g. "42,123,456")

**Behavior:**
1. Validate input PNG exists
2. If `--seeds` given: run batch, save as `{stem}_seed{seed}.mp4` each
3. Activate `FRAMEPACK_VENV` via subprocess or `activate_this.py`
4. Call FramePack's inference (via its demo script or direct import)
5. Save output MP4, print path to stdout

**FramePack calling convention:**
```python
# Option A: subprocess into its venv python
cmd = [str(FRAMEPACK_VENV / "Scripts" / "python"), 
       str(FRAMEPACK_DIR / "demo_gradio.py"), ...]

# Option B: call Gradio API if server already running
import requests
# POST to http://127.0.0.1:7860/...
```

Start with Option A (subprocess), add Option B later for speed.

## run_wan22.py — Spec

Wan 2.2 runs via ComfyUI, so this script:
1. Reads the workflow JSON from `workflows/wan22_i2v.json`
2. Patches in the input image path and prompt
3. POSTs to ComfyUI's `/prompt` endpoint
4. Polls `/history/{prompt_id}` until done
5. Downloads the output video from `/view`

```python
import requests, json, time
from pathlib import Path

def queue_workflow(workflow: dict) -> str:
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    return r.json()["prompt_id"]

def wait_for_output(prompt_id: str) -> Path:
    while True:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        history = r.json()
        if prompt_id in history:
            outputs = history[prompt_id]["outputs"]
            # find video node output, download it
            ...
        time.sleep(2)
```

## run_liveportrait.py — Spec

**Inputs:**
- `input_png`: Path — portrait to animate
- `output_mp4`: Path
- `--driving`: str — "webcam" or path to driving video

**Behavior:**
1. If `--driving webcam`: launch LivePortrait in real-time mode
2. If `--driving path`: run inference on driving video
3. Output is face-region animation — may need compositing back onto source

## Implementation Order

1. Write `config.py` — all paths
2. Write `run_framepack.py` — subprocess wrapper, basic single-image mode
3. Test end-to-end with a real PNG → verify raw MP4 output
4. Add batch mode (`--seeds`) to `run_framepack.py`
5. Install ComfyUI + Wan 2.2 weights
7. Write `run_wan22.py` — ComfyUI API wrapper
8. Test Wan 2.2 end-to-end
9. Install LivePortrait, write `run_liveportrait.py`
10. Integration test: all three backends → raw MP4 → pipe to convert

## Backend Performance Summary (RTX 5090)

### FramePack
- Model: HunyuanVideo 13B (fp8, ~30GB download on first run)
- VRAM: ~12GB
- Speed: ~0.8-1.2s per frame → 5s@30fps clip in ~2-3 min
- Quality: Good, best for iteration

### Wan 2.2 14B
- VRAM: ~20GB fp16 (no quantization needed on 5090)
- Speed: ~30-50 min per 2.3s at 720p
- Quality: Best available, use for final renders

### Wan 2.2 5B
- VRAM: ~12GB
- Speed: ~5-10 min per 2.3s at 720p
- Quality: Good middle ground

### LivePortrait
- VRAM: ~4GB
- Speed: near real-time
- Quality: Face only — use as supplement, not primary
