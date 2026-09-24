import argparse
import json
from pathlib import Path

from app.core.config import settings
from app.services.clip_export import run_ffmpeg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render goal-detection manifest windows as compact MP4 clips"
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        raise SystemExit("Dataset manifest not found.")
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else manifest_path.parent / "clips"
    )
    samples = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()]
    if args.limit is not None:
        samples = samples[: args.limit]

    rendered = 0
    skipped = 0
    for index, sample in enumerate(samples, start=1):
        source_path = settings.video_storage_path / sample["video_storage_key"]
        if not source_path.is_file():
            raise SystemExit(f"Source video not found: {source_path}")
        clip_path = (
            output_dir
            / sample["split"]
            / sample["label"]
            / f"{sample['sample_id']}.mp4"
        )
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        if clip_path.is_file() and clip_path.stat().st_size > 0:
            skipped += 1
            continue
        start = float(sample["start_seconds"])
        duration = float(sample["end_seconds"]) - start
        run_ffmpeg(
            [
                "-ss",
                f"{start:.3f}",
                "-i",
                str(source_path),
                "-t",
                f"{duration:.3f}",
                "-map",
                "0:v:0",
                "-an",
                "-vf",
                "fps=8,scale=-2:256",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-movflags",
                "+faststart",
                str(clip_path),
            ]
        )
        rendered += 1
        print(f"[{index}/{len(samples)}] {clip_path.relative_to(output_dir)}")

    print(f"Rendered {rendered} clips; reused {skipped} existing clips in {output_dir}")


if __name__ == "__main__":
    main()
