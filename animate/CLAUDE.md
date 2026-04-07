# animate/ — Agent Context

AI animation subproject. Takes a static PNG, outputs a raw MP4. See root [CLAUDE.md](../CLAUDE.md) for full project context.

## What This Does

Wraps three AI video generation backends behind a consistent CLI so `orchestrate.py` can call any of them. Output is always raw MP4 at native resolution — `convert/` handles upscaling and encoding.

## Stack

- `uv` for top-level deps (just `requests` + `pytest`). Run with `uv run`.
- Each backend lives in `backends/<name>/` with its **own separate venv** — never use the top-level `.venv` for backend inference.
- The `run_*.py` wrapper scripts activate the backend venv and call inference via subprocess.

## Backends

| Script | Backend | VRAM | Speed (RTX 5090) | Status |
|---|---|---|---|---|
| `run_framepack.py` | FramePack (HunyuanVideo 13B) | ~12GB | ~2-3 min / 5s clip | not yet cloned |
| `run_wan22.py` | Wan 2.2 I2V via ComfyUI API | ~20GB | ~30-50 min / 2.3s | not yet set up |
| `run_liveportrait.py` | LivePortrait (face only) | ~4GB | near real-time | not yet cloned |

## Wrapper Script Pattern

Each `run_*.py` follows this structure:
```python
# 1. Parse args: input_png, output_mp4/dir, --prompt, --seconds, --seed, --seeds (batch)
# 2. Validate input exists
# 3. Activate backend venv (subprocess into backends/<name>/venv/Scripts/python)
# 4. Call backend inference
# 5. Print output path to stdout (orchestrate.py reads this)
# 6. Batch mode: --seeds "42,123,456" → saves {stem}_seed{N}.mp4 for each
```

## Backend Setup (when ready)

**FramePack** (start here):
```bash
cd backends
git clone https://github.com/lllyasviel/FramePack.git framepack
cd framepack && py -m venv venv
venv\Scripts\activate.bat
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt && pip install sageattention==1.0.6
# ~30GB HunyuanVideo weights download on first inference run
```

**Wan 2.2**: Install ComfyUI separately. Set `COMFYUI_URL` in `config.py` (default: `http://127.0.0.1:8188`). Download Wan 2.2 I2V weights to ComfyUI's `models/` dir.

**LivePortrait**:
```bash
cd backends
git clone https://github.com/KwaiVGI/LivePortrait.git liveportrait
cd liveportrait && py -m venv venv
venv\Scripts\activate.bat
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements.txt
```

## Prompt Guidance

Keep prompts minimal and environmental — these models preserve source art best with subtle effects:
- Good: `silver hair swaying gently, ribbons flutter, slow blink, gentle breathing`
- Bad: anything involving character action (dancing, running, talking, dramatic expressions)

## Key Files to Create

1. `config.py` — backend dirs, venv paths, ComfyUI URL, output dir
2. `run_framepack.py` — primary wrapper
3. `run_wan22.py` — ComfyUI API client
4. `run_liveportrait.py` — LivePortrait wrapper
