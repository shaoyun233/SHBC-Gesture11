#!/usr/bin/env python3
"""Verify release archives or an extracted SHBC-Gesture11 dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive-dir", type=Path, default=DATASET_ROOT / "archives"
    )
    parser.add_argument("--check-frames", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(
        (DATASET_ROOT / "release_manifest.json").read_text(encoding="utf-8")
    )
    archives = args.archive_dir.resolve()
    checked = 0
    for item in manifest:
        path = archives / item["file"]
        if not path.is_file():
            raise SystemExit(f"Missing archive: {path}")
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise SystemExit(f"Archive verification failed: {path.name}")
        checked += 1
    print(f"Verified {checked} release archives.")
    if args.check_frames:
        frame_count = sum(1 for _ in (DATASET_ROOT / "frames").rglob("*.jpg"))
        expected = sum(int(item["frames"]) for item in manifest)
        if frame_count != expected:
            raise SystemExit(f"Expected {expected} frames, found {frame_count}")
        print(f"Verified extracted frame count: {frame_count}")


if __name__ == "__main__":
    main()
