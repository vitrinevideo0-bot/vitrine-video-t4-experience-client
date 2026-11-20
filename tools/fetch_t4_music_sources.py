#!/usr/bin/env python3
"""Fetch T4 music only from the official Pixabay CDN and verify every SHA-256."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "audio/music/t4-afrobeat-v1/source_manifest.json")
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache/t4-music-originals")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    args.cache.mkdir(parents=True, exist_ok=True)
    for track in data["tracks"]:
        url = track["official_download_url"]
        page = track["official_page"]
        if not url.startswith("https://cdn.pixabay.com/download/audio/"):
            raise RuntimeError(f"Non-official music URL refused: {url}")
        target = args.cache / track["source"]["cache_filename"]
        expected = track["source"]["sha256"]
        if target.exists() and sha256(target) == expected:
            print(f"CACHE PASS {track['choice']} {target}")
            continue
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (T4 reproducible music source fetch)",
            "Referer": page,
            "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.1",
        })
        error: Exception | None = None
        for attempt in range(1, 6):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    payload = response.read()
                target.write_bytes(payload)
                error = None
                break
            except Exception as exc:
                error = exc
                time.sleep(attempt)
        if error is not None:
            raise error
        if sha256(target) != expected or target.stat().st_size != int(track["source"]["bytes"]):
            target.unlink(missing_ok=True)
            raise RuntimeError(f"Official source integrity failure after download: {target}")
        print(f"DOWNLOAD PASS {track['choice']} {target}")
    print("T4_OFFICIAL_MUSIC_SOURCES 4/4 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
