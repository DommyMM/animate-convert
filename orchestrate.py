"""
orchestrate.py — chains animate and convert

No dependencies beyond stdlib. Calls each project's CLI via subprocess.

Usage:
    python orchestrate.py --input input/gacha_girl.png --output output/ --backend framepack \
        --prompt "silver hair swaying gently" --seconds 5 --seed 42 \
        --upscale 4 --format mp4 --resolution 4k --loop
"""
import subprocess
import argparse
import sys
import shutil
from pathlib import Path

ANIMATE_DIR = Path(__file__).parent / "animate"
CONVERT_DIR = Path(__file__).parent / "convert"

RESOLUTION_PRESETS = {
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k":    (3840, 2160),
}


def run_animate(input_png: Path, output_mp4: Path, backend: str, prompt: str, seconds: int, seed: int | None) -> Path:
    """Call animate CLI, return path to raw MP4."""
    cmd = [
        sys.executable,
        str(ANIMATE_DIR / f"run_{backend}.py"),
        str(input_png),
        str(output_mp4),
        "--prompt", prompt,
        "--seconds", str(seconds),
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    print(f"[animate] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return output_mp4


def run_postprocess(input_mp4: Path, output_path: Path, upscale: int, fmt: str, resolution: str, loop: bool) -> Path:
    """Call convert CLI for upscale + convert + loop."""
    w, h = RESOLUTION_PRESETS.get(resolution, (3840, 2160))
    cmd = [
        sys.executable, "-m", "convert",
        "pipeline", "wallpaper",
        str(input_mp4),
        str(output_path),
        "--scale", str(upscale),
        "--format", fmt,
        "--width", str(w),
        "--height", str(h),
    ]
    if loop:
        cmd.append("--loop")
    print(f"[postprocess] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PNG → animated 4K wallpaper pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline
  python orchestrate.py --input input/girl.png --output output/ --backend framepack \\
      --prompt "silver hair swaying gently" --seconds 5 --seed 42 \\
      --upscale 4 --format mp4 --resolution 4k --loop

  # Skip animation (already have a clip)
  python orchestrate.py --input input/clip.mp4 --output output/ \\
      --skip-animate --upscale 2 --format gif --resolution 1080p --loop

  # Animate only
  python orchestrate.py --input input/girl.png --output output/ \\
      --backend framepack --prompt "hair blowing" --skip-postprocess
        """,
    )
    parser.add_argument("--input", required=True, type=Path, help="Input PNG or MP4")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--backend", default="framepack",
                        choices=["framepack", "wan", "face"],
                        help="Animation backend (default: framepack)")
    parser.add_argument("--prompt", default="gentle ambient motion",
                        help="Animation prompt")
    parser.add_argument("--seconds", type=int, default=5,
                        help="Clip length in seconds (default: 5)")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducibility")
    parser.add_argument("--upscale", type=int, default=4,
                        help="Upscale factor (default: 4)")
    parser.add_argument("--format", default="mp4",
                        choices=["mp4", "gif", "webp", "apng"],
                        help="Output format (default: mp4)")
    parser.add_argument("--resolution", default="4k",
                        choices=list(RESOLUTION_PRESETS.keys()),
                        help="Target resolution preset (default: 4k)")
    parser.add_argument("--loop", action="store_true",
                        help="Create seamless loop via crossfade")
    parser.add_argument("--skip-animate", action="store_true",
                        help="Skip animation step (input must be MP4)")
    parser.add_argument("--skip-postprocess", action="store_true",
                        help="Skip post-processing, output raw animation only")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    intermediate = args.output / "raw_animation.mp4"

    if not args.skip_animate:
        run_animate(args.input, intermediate,
                    args.backend, args.prompt, args.seconds, args.seed)
    else:
        shutil.copy2(args.input, intermediate)

    if not args.skip_postprocess:
        ext = args.format if args.format != "mp4" else "mp4"
        final = args.output / f"{args.input.stem}_animated.{ext}"
        run_postprocess(intermediate, final,
                        args.upscale, args.format, args.resolution, args.loop)
        print(f"\nDone: {final}")
    else:
        print(f"\nDone: {intermediate}")


if __name__ == "__main__":
    main()
