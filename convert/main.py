"""
convert — local media processing CLI

Usage:
    uv run python -m convert <command> [options]
    uv run python -m convert --help
"""
import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from convert import config

app = typer.Typer(help="Local media processing: upscale, convert, optimize, loop.")
console = Console()


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
        console.print(f"Upscaling video [cyan]{input}[/cyan] → [cyan]{output}[/cyan] ({scale}x, {model})")
        upscale_then_mp4(input, output, scale=scale, model=model)
    else:
        console.print(f"Upscaling image [cyan]{input}[/cyan] → [cyan]{output}[/cyan] ({scale}x, {model})")
        upscale_image(input, output, scale=scale, model=model)
    console.print(f"[green]Done:[/green] {output}")


# ---------------------------------------------------------------------------
# convert (generic)
# ---------------------------------------------------------------------------

@app.command(name="convert")
def convert_cmd(
    input:   Annotated[Path, typer.Argument(help="Input video or GIF")],
    output:  Annotated[Path, typer.Argument(help="Output path (extension determines format)")],
    fps:     Annotated[float | None, typer.Option(help="Output fps")] = None,
    width:   Annotated[int | None,   typer.Option(help="Output width (height auto)")] = None,
):
    """Convert video ↔ GIF ↔ MP4. Format inferred from output extension."""
    from convert.converters.to_gif import video_to_gif
    from convert.converters.to_mp4 import video_to_mp4

    ext = output.suffix.lower()
    if ext == ".gif":
        console.print(f"Converting [cyan]{input}[/cyan] → GIF")
        video_to_gif(input, output, fps=fps or config.DEFAULT_FPS, width=width)
    elif ext in {".mp4", ".mkv"}:
        console.print(f"Converting [cyan]{input}[/cyan] → MP4")
        video_to_mp4(input, output, fps=fps, width=width)
    else:
        console.print(f"[red]Unknown output format:[/red] {ext}")
        raise typer.Exit(1)
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
    console.print(f"Upscale→GIF [cyan]{input}[/cyan] → [cyan]{output}[/cyan] ({scale}x, {fps}fps)")
    upscale_then_gif(input, output, scale=scale, fps=fps, width=width, colors=colors, lossy=lossy, model=model)
    console.print(f"[green]Done:[/green] {output}  ({output.stat().st_size // 1024} KB)")


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
    before = input.stat().st_size // 1024
    after = output.stat().st_size // 1024
    console.print(f"[green]Done:[/green] {before} KB → {after} KB ({100 - after * 100 // before}% smaller)")


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
