#!/usr/bin/env python3
"""Download and verify the four Pexels T4 demo rushes.

Raw media remains in rushes/cache (Git-ignored) and is never uploaded as a
standalone artifact or Release asset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

CHUNK = 1024 * 1024
USER_AGENT = "VitrineVideo-T4/1.0 (+https://github.com/vitrinevideo0-bot)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, destination: Path, attempts: int = 4) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
                while True:
                    block = response.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
            os.replace(partial, destination)
            return
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt == attempts:
                raise
            time.sleep(2 ** attempt)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("rushes/manifest.json"))
    parser.add_argument("--cache", type=Path, default=Path("rushes/cache"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    results = []
    for scene in manifest["scenes"]:
        target = args.cache / scene["cache_filename"]
        expected_hash = scene["sha256"]
        expected_bytes = int(scene["expected_bytes"])
        valid_cache = target.exists() and target.stat().st_size == expected_bytes and sha256(target) == expected_hash
        if not valid_cache:
            target.unlink(missing_ok=True)
            print(f"DOWNLOAD {scene['scene']} {scene['download_url']}", flush=True)
            download(scene["download_url"], target)
        actual_hash = sha256(target)
        actual_bytes = target.stat().st_size
        if actual_bytes != expected_bytes:
            raise SystemExit(f"Invalid size for {target}: {actual_bytes} != {expected_bytes}")
        if actual_hash != expected_hash:
            raise SystemExit(f"Invalid SHA-256 for {target}: {actual_hash} != {expected_hash}")
        results.append({
            "scene": scene["scene"],
            "pexels_id": scene["pexels_id"],
            "page_url": scene["page_url"],
            "file": str(target),
            "bytes": actual_bytes,
            "sha256": actual_hash,
            "verified": True,
        })
        print(f"VERIFIED {scene['scene']} {actual_bytes} {actual_hash}")

    proof = args.cache / "FETCH_PROOF.json"
    proof.write_text(json.dumps({
        "schema_version": "1.0.0",
        "template_id": manifest["template_id"],
        "provider": manifest["license"]["provider"],
        "license_url": manifest["license"]["license_url"],
        "raw_media_committed": False,
        "raw_media_publish_forbidden": True,
        "results": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"FETCH_RUSHES_PASS {proof}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
