#!/usr/bin/env python3
"""Download, verify, and safely extract SHBC-Gesture11 release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


DATASET_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = DATASET_ROOT / "release_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def infer_repository() -> str | None:
    try:
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=DATASET_ROOT.parent,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", remote)
    return match.group(1) if match else None


def request(url: str, headers: dict[str, str] | None = None):
    base_headers = {"Accept": "application/vnd.github+json", "User-Agent": "SHBC-Gesture11"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        base_headers["Authorization"] = f"Bearer {token}"
    if headers:
        base_headers.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=base_headers))


def release_assets(repository: str, tag: str) -> dict[str, str]:
    suffix = "latest" if tag == "latest" else f"tags/{tag}"
    with request(f"https://api.github.com/repos/{repository}/releases/{suffix}") as response:
        release = json.load(response)
    return {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}


def download(url: str, target: Path, expected_bytes: int) -> None:
    current = target.stat().st_size if target.exists() else 0
    if current == expected_bytes:
        return
    headers = {"Range": f"bytes={current}-"} if current else {}
    mode = "ab" if current else "wb"
    try:
        response = request(url, headers)
    except urllib.error.HTTPError as error:
        if error.code == 416 and target.exists():
            return
        raise
    if current and response.status != 206:
        mode = "wb"
        current = 0
    total = int(response.headers.get("Content-Length", "0")) + current
    with response, target.open(mode) as handle:
        received = current
        while chunk := response.read(1024 * 1024):
            handle.write(chunk)
            received += len(chunk)
            print(
                f"\r{target.name}: {received / 1024**2:.1f}/{total / 1024**2:.1f} MiB",
                end="",
                flush=True,
            )
    print()


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != destination and destination not in target.parents:
                raise RuntimeError(f"Unsafe archive path: {member.filename}")
        archive.extractall(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=None, help="GitHub repository as OWNER/REPO")
    parser.add_argument("--tag", default="v1.0.0")
    parser.add_argument("--archive-dir", type=Path, default=DATASET_ROOT / "archives")
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()

    repository = args.repo or infer_repository()
    if not repository:
        raise SystemExit("Pass --repo OWNER/REPO or configure a GitHub origin remote.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assets = release_assets(repository, args.tag)
    args.archive_dir.mkdir(parents=True, exist_ok=True)
    for item in manifest:
        name = item["file"]
        if name not in assets:
            raise SystemExit(f"Release asset is missing: {name}")
        target = args.archive_dir / name
        if not target.exists() or sha256(target) != item["sha256"]:
            download(assets[name], target, int(item["bytes"]))
        actual = sha256(target)
        if actual != item["sha256"]:
            raise SystemExit(f"SHA-256 mismatch: {name}")
        print(f"verified {name}")
        if args.extract:
            safe_extract(target, DATASET_ROOT)
            print(f"extracted {name}")
    print("SHBC-Gesture11 dataset is ready.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Download interrupted; rerun the same command to resume.")
