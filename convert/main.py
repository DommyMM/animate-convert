"""
convert — local media processing CLI

Usage:
    uv run convert <command> [options]
    uv run convert --help
"""
import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from convert import config

app = typer.Typer(help="Local media processing: convert, upscale, optimize, loop.")
console = Console()


def _size_str(path: Path) -> str:
    size = path.stat().st_size
    if size > 1_048_576:
        return f"{size / 1_048_576:.1f} MB"
    return f"{size // 1024} KB"


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

@app.command()
def check():
    """Verify all external binaries are present and print their paths."""
    binaries = {
        "ffmpeg":                  config.FFMPEG,
        "ffprobe":                 config.FFPROBE,
        "magick (ImageMagick)":    config.MAGICK,
        "gifski":                  config.GIFSKI,
        "gifsicle":                config.GIFSICLE,
        "realesrgan-ncnn-vulkan":  config.REALESRGAN,
        "waifu2x-ncnn-vulkan":     config.WAIFU2X,
    }
    table = Table(title="Binary Status")
    table.add_column("Binary", style="cyan")
    table.add_column("Path")
    table.add_column("Status")

    all_ok = True
    for name, path in binaries.items():
        if path is None:
            table.add_row(name, "—", "[yellow]optional / not found[/yellow]")
        elif path.exists():
            table.add_row(name, str(path), "[green]OK[/green]")
        else:
            table.add_row(name, str(path), "[red]MISSING[/red]")
            all_ok = False

    console.print(table)
    if not all_ok:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------

@app.command()
def info(input: Annotated[Path, typer.Argument(help="Video or GIF to inspect")]):
    """Print video metadata (fps, resolution, duration, frame count)."""
    from convert.core.ffmpeg import get_video_info
    data = get_video_info(input)
    table = Table(title=str(input))
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(k, str(round(v, 3) if isinstance(v, float) else v))
    console.print(table)


# ---------------------------------------------------------------------------
# convert (generic — format from output extension)
# ---------------------------------------------------------------------------

@app.command(name="convert")
def convert_cmd(
    input:    Annotated[Path, typer.Argument(help="Input file")],
    output:   Annotated[Path, typer.Argument(help="Output path (extension determines format)")],
    fps:      Annotated[float | None, typer.Option(help="Output fps")] = None,
    width:    Annotated[int | None,   typer.Option(help="Resize width (height auto)")] = None,
    quality:  Annotated[int, typer.Option(help="Quality for WebP (0-100)")] = 80,
    colors:   Annotated[int, typer.Option(help="GIF palette size")] = config.DEFAULT_GIF_COLORS,
    lossy:    Annotated[int | None, typer.Option(help="GIF lossy level (40-100)")] = None,
):
    """Convert between formats. Output format inferred from extension."""
    ext = output.suffix.lower()
    console.print(f"Converting [cyan]{input}[/cyan] → [cyan]{output}[/cyan]")

    if ext == ".gif":
        from convert.converters.to_gif import video_to_gif
        video_to_gif(input, output, fps=fps or config.DEFAULT_FPS, width=width, colors=colors, lossy=lossy)
    elif ext in {".mp4", ".mkv", ".mov"}:
        from convert.converters.to_mp4 import video_to_mp4
        video_to_mp4(input, output, fps=fps, width=width)
    elif ext == ".webp":
        from convert.converters.to_webp import video_to_webp
        video_to_webp(input, output, fps=fps, width=width, quality=quality)
    elif ext in {".apng", ".png"}:
        if ext == ".png" and input.suffix.lower() in {".mp4", ".mkv", ".webm", ".avi", ".mov", ".gif", ".webp"}:
            from convert.converters.to_apng import video_to_apng
            video_to_apng(input, output, fps=fps, width=width)
        else:
            # Static image conversion via ffmpeg
            from convert.core.ffmpeg import _run
            cmd = [str(config.FFMPEG), "-y", "-i", str(input)]
            if width:
                cmd += ["-vf", f"scale={width}:-2"]
            cmd += [str(output)]
            _run(cmd)
    else:
        # Fallback: let ffmpeg figure it out
        from convert.core.ffmpeg import _run
        cmd = [str(config.FFMPEG), "-y", "-i", str(input)]
        if fps:
            cmd += ["-r", str(fps)]
        if width:
            cmd += ["-vf", f"scale={width}:-2"]
        cmd += [str(output)]
        _run(cmd)

    console.print(f"[green]Done:[/green] {output}  ({_size_str(output)})")


# ---------------------------------------------------------------------------
# trim
# ---------------------------------------------------------------------------

@app.command()
def trim(
    input:    Annotated[Path, typer.Argument(help="Input video")],
    output:   Annotated[Path, typer.Argument(help="Output video")],
    start:    Annotated[float | None, typer.Option(help="Start time in seconds")] = None,
    end:      Annotated[float | None, typer.Option(help="End time in seconds")] = None,
    duration: Annotated[float | None, typer.Option(help="Duration in seconds (alternative to --end)")] = None,
):
    """Trim a video to a time range."""
    from convert.core.ffmpeg import trim as _trim
    console.print(f"Trimming [cyan]{input}[/cyan] (start={start}, end={end}, duration={duration})")
    _trim(input, output, start=start, end=end, duration=duration)
    console.print(f"[green]Done:[/green] {output}  ({_size_str(output)})")


# ---------------------------------------------------------------------------
# resize
# ---------------------------------------------------------------------------

@app.command(name="resize")
def resize_cmd(
    input:  Annotated[Path, typer.Argument(help="Input video")],
    output: Annotated[Path, typer.Argument(help="Output video")],
    width:  Annotated[int, typer.Argument(help="Target width (height auto)")],
    height: Annotated[int, typer.Option(help="Target height (-2 = auto)")] = -2,
):
    """Resize a video."""
    from convert.core.ffmpeg import resize as _resize
    console.print(f"Resizing [cyan]{input}[/cyan] → {width}×{height}")
    _resize(input, output, width=width, height=height)
    console.print(f"[green]Done:[/green] {output}  ({_size_str(output)})")


# ---------------------------------------------------------------------------
# speed
# ---------------------------------------------------------------------------

@app.command()
def speed(
    input:  Annotated[Path, typer.Argument(help="Input video")],
    output: Annotated[Path, typer.Argument(help="Output video")],
    factor: Annotated[float, typer.Argument(help="Speed factor (2.0 = 2x faster, 0.5 = half speed)")],
):
    """Change video playback speed."""
    from convert.core.ffmpeg import change_speed
    console.print(f"Speed [cyan]{input}[/cyan] × {factor}")
    change_speed(input, output, factor=factor)
    console.print(f"[green]Done:[/green] {output}  ({_size_str(output)})")


# ---------------------------------------------------------------------------
# reverse
# ---------------------------------------------------------------------------

@app.command(name="reverse")
def reverse_cmd(
    input:  Annotated[Path, typer.Argument(help="Input video")],
    output: Annotated[Path, typer.Argument(help="Output video")],
):
    """Reverse a video."""
    from convert.core.ffmpeg import reverse as _reverse
    console.print(f"Reversing [cyan]{input}[/cyan]")
    _reverse(input, output)
    console.print(f"[green]Done:[/green] {output}  ({_size_str(output)})")


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------

@app.command()
def optimize(
    input:   Annotated[Path, typer.Argument(help="Input .gif")],
    output:  Annotated[Path, typer.Argument(help="Output .gif")],
    level:   Annotated[int, typer.Option(help="gifsicle -O level (1-3)")] = 3,
    lossy:   Annotated[int | None, typer.Option(help="gifsicle lossy level (40-100)")] = None,
    colors:  Annotated[int, typer.Option()] = config.DEFAULT_GIF_COLORS,
):
    """Optimize a GIF with gifsicle."""
    import subprocess
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input, output)
    cmd = [str(config.GIFSICLE), f"-O{level}", "--colors", str(colors), "--batch", str(output)]
    if lossy:
        cmd += [f"--lossy={lossy}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    before = input.stat().st_size
    after = output.stat().st_size
    pct = 100 - after * 100 // before if before else 0
    console.print(f"[green]Done:[/green] {_size_str(input)} → {_size_str(output)} ({pct}% smaller)")


# ---------------------------------------------------------------------------
# loop
# ---------------------------------------------------------------------------

@app.command(name="loop")
def loop_cmd(
    input:            Annotated[Path, typer.Argument(help="Input video")],
    output:           Annotated[Path, typer.Argument(help="Output video")],
    crossfade_frames: Annotated[int, typer.Option(help="Frames to crossfade")] = config.DEFAULT_CROSSFADE_FRAMES,
):
    """Make a video loop seamlessly via crossfade blending."""
    from convert.tools.loop import make_seamless_loop
    console.print(f"Looping [cyan]{input}[/cyan] ({crossfade_frames} crossfade frames)")
    make_seamless_loop(input, output, crossfade_frames=crossfade_frames)
    console.print(f"[green]Done:[/green] {output}")


# ---------------------------------------------------------------------------
# upscale
# ---------------------------------------------------------------------------

@app.command()
def upscale(
    input:  Annotated[Path, typer.Argument(help="Input image or video")],
    output: Annotated[Path, typer.Argument(help="Output path")],
    scale:  Annotated[int,  typer.Option(help="Scale factor (2 or 4)")] = 4,
    model:  Annotated[str,  typer.Option(help="Real-ESRGAN model name")] = config.DEFAULT_REALESRGAN_MODEL,
):
    """Upscale an image or video via Real-ESRGAN (Vulkan)."""
    from convert.upscale.realesrgan import upscale_image
    if input.suffix.lower() in {".mp4", ".mkv", ".webm", ".avi", ".mov", ".gif"}:
        from convert.core.pipeline import upscale_then_mp4
        console.print(f"Upscaling video [cyan]{input}[/cyan] ({scale}x, {model})")
        upscale_then_mp4(input, output, scale=scale, model=model)
    else:
        console.print(f"Upscaling image [cyan]{input}[/cyan] ({scale}x, {model})")
        upscale_image(input, output, scale=scale, model=model)
    console.print(f"[green]Done:[/green] {output}")


# ---------------------------------------------------------------------------
# upscale-gif
# ---------------------------------------------------------------------------

@app.command(name="upscale-gif")
def upscale_gif(
    input:   Annotated[Path, typer.Argument(help="Input video or GIF")],
    output:  Annotated[Path, typer.Argument(help="Output .gif path")],
    scale:   Annotated[int,  typer.Option()] = 2,
    fps:     Annotated[float, typer.Option()] = config.DEFAULT_FPS,
    width:   Annotated[int | None, typer.Option()] = None,
    colors:  Annotated[int, typer.Option()] = config.DEFAULT_GIF_COLORS,
    lossy:   Annotated[int | None, typer.Option(help="gifsicle lossy level (40-100)")] = None,
    model:   Annotated[str, typer.Option()] = config.DEFAULT_REALESRGAN_MODEL,
):
    """Upscale frames then encode as GIF (gifski + gifsicle)."""
    from convert.core.pipeline import upscale_then_gif
    console.print(f"Upscale→GIF [cyan]{input}[/cyan] ({scale}x, {fps}fps)")
    upscale_then_gif(input, output, scale=scale, fps=fps, width=width, colors=colors, lossy=lossy, model=model)
    console.print(f"[green]Done:[/green] {output}  ({_size_str(output)})")


# ---------------------------------------------------------------------------
# pipeline wallpaper
# ---------------------------------------------------------------------------

pipeline_app = typer.Typer(help="Multi-step pipeline presets.")
app.add_typer(pipeline_app, name="pipeline")


@pipeline_app.command(name="wallpaper")
def pipeline_wallpaper(
    input:            Annotated[Path, typer.Argument(help="Raw animation MP4")],
    output:           Annotated[Path, typer.Argument(help="Output path")],
    scale:            Annotated[int, typer.Option()] = 4,
    fmt:              Annotated[str, typer.Option("--format")] = "mp4",
    width:            Annotated[int, typer.Option()] = 3840,
    height:           Annotated[int, typer.Option()] = 2160,
    loop:             Annotated[bool, typer.Option()] = True,
    crossfade_frames: Annotated[int, typer.Option()] = config.DEFAULT_CROSSFADE_FRAMES,
    model:            Annotated[str, typer.Option()] = config.DEFAULT_REALESRGAN_MODEL,
):
    """Full 4K wallpaper pipeline: upscale → loop → pad/crop → encode."""
    from convert.core.pipeline import animate_to_4k_wallpaper
    console.print(
        f"Wallpaper pipeline: [cyan]{input}[/cyan] → [cyan]{output}[/cyan]\n"
        f"  {scale}x upscale | {width}×{height} | format={fmt} | loop={loop}"
    )
    animate_to_4k_wallpaper(
        input, output,
        target_width=width, target_height=height,
        scale=scale, output_format=fmt,
        loop=loop, crossfade_frames=crossfade_frames, model=model,
    )
    console.print(f"[green]Done:[/green] {output}")
