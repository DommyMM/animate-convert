"""
High-level pipelines that chain modules together.

Each pipeline function manages its own temp directory and cleans up on success.
"""
import uuid
import shutil
from pathlib import Path

from convert.config import (
    TEMP_DIR, DEFAULT_FPS, DEFAULT_GIF_COLORS,
    DEFAULT_REALESRGAN_MODEL, DEFAULT_CROSSFADE_FRAMES,
)
from convert.core.ffmpeg import extract_frames, frames_to_video, get_video_info, pad_crop_to
from convert.upscale.realesrgan import upscale_frames
from convert.converters.to_gif import frames_to_gif
from convert.converters.to_mp4 import frames_to_mp4
from convert.tools.loop import make_seamless_loop


def _tmpdir() -> Path:
    d = TEMP_DIR / uuid.uuid4().hex
    d.mkdir(parents=True, exist_ok=True)
    return d


def upscale_then_gif(
    input: Path,
    output: Path,
    scale: int = 2,
    fps: float = DEFAULT_FPS,
    width: int | None = None,
    colors: int = DEFAULT_GIF_COLORS,
    lossy: int | None = None,
    model: str = DEFAULT_REALESRGAN_MODEL,
) -> Path:
    """MP4/GIF → extract frames → upscale → gifski → gifsicle → output GIF."""
    tmp = _tmpdir()
    try:
        raw_frames = tmp / "raw"
        up_frames = tmp / "upscaled"

        extract_frames(input, raw_frames, fps=fps)
        upscale_frames(raw_frames, up_frames, scale=scale, model=model)

        result = frames_to_gif(
            sorted(up_frames.glob("*.png")),
            output,
            fps=fps, width=width, colors=colors, lossy=lossy,
        )
        shutil.rmtree(tmp)
        return result
    except Exception:
        # Preserve tmp on failure for debugging
        print(f"[pipeline] temp files preserved at {tmp}")
        raise


def upscale_then_mp4(
    input: Path,
    output: Path,
    scale: int = 4,
    fps: float | None = None,
    model: str = DEFAULT_REALESRGAN_MODEL,
    nvenc: bool = True,
) -> Path:
    """MP4 → extract frames → upscale → NVENC H.265 → output MP4."""
    tmp = _tmpdir()
    try:
        info = get_video_info(input)
        out_fps = fps or info["fps"]
        raw_frames = tmp / "raw"
        up_frames = tmp / "upscaled"

        extract_frames(input, raw_frames, fps=fps)
        upscale_frames(raw_frames, up_frames, scale=scale, model=model)

        result = frames_to_mp4(up_frames, output, fps=out_fps, nvenc=nvenc)
        shutil.rmtree(tmp)
        return result
    except Exception:
        print(f"[pipeline] temp files preserved at {tmp}")
        raise


def animate_to_4k_wallpaper(
    input: Path,
    output: Path,
    target_width: int = 3840,
    target_height: int = 2160,
    scale: int = 4,
    model: str = DEFAULT_REALESRGAN_MODEL,
    output_format: str = "mp4",
    fps: float | None = None,
    loop: bool = True,
    crossfade_frames: int = DEFAULT_CROSSFADE_FRAMES,
    gif_colors: int = DEFAULT_GIF_COLORS,
    gif_lossy: int | None = None,
) -> Path:
    """
    Full pipeline: raw animation clip → 4K wallpaper-ready output.

    Steps:
      1. Extract frames at source fps
      2. Upscale all frames via Real-ESRGAN (Vulkan)
      3. Seamless loop crossfade (if loop=True)
      4. Pad/crop reassembled video to exact target resolution
      5. Encode to output_format (mp4, gif, webp, apng)

    For 4K always use output_format="mp4". GIF at 3840×2160 is 80-350MB
    and capped at 256 colors. Wallpaper Engine and Lively accept MP4 directly.
    """
    tmp = _tmpdir()
    try:
        info = get_video_info(input)
        out_fps = fps or info["fps"]

        # 1. Extract
        raw_frames = tmp / "raw"
        extract_frames(input, raw_frames, fps=fps)

        # 2. Upscale
        up_frames = tmp / "upscaled"
        upscale_frames(raw_frames, up_frames, scale=scale, model=model)

        # 3. Reassemble to intermediate MP4
        intermediate = tmp / "upscaled.mp4"
        frames_to_mp4(up_frames, intermediate, fps=out_fps, nvenc=True)

        # 4. Seamless loop
        if loop:
            looped = tmp / "looped.mp4"
            make_seamless_loop(intermediate, looped, crossfade_frames=crossfade_frames)
            intermediate = looped

        # 5. Pad/crop to exact target resolution
        sized = tmp / "sized.mp4"
        pad_crop_to(intermediate, sized, width=target_width, height=target_height)

        # 6. Encode to final format
        output.parent.mkdir(parents=True, exist_ok=True)
        if output_format == "mp4":
            # Already H.265 from above — just copy
            shutil.copy2(sized, output)
        elif output_format == "gif":
            gif_frames = tmp / "gif_frames"
            extract_frames(sized, gif_frames, fps=min(out_fps, DEFAULT_FPS))
            frames_to_gif(
                sorted(gif_frames.glob("*.png")),
                output,
                fps=min(out_fps, DEFAULT_FPS),
                colors=gif_colors,
                lossy=gif_lossy,
            )
        else:
            raise ValueError(f"Unsupported output_format: {output_format!r}. Use 'mp4' or 'gif'.")

        shutil.rmtree(tmp)
        return output
    except Exception:
        print(f"[pipeline] temp files preserved at {tmp}")
        raise
