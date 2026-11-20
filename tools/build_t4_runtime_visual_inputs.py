#!/usr/bin/env python3
"""Validate four R2 captures and build inputs for the approved T4 V3 visual engine."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

DURATIONS = {"S1": 6, "S2": 8, "S3": 7, "S4": 9}
FRAMES = {"S1": [0, 179], "S2": [180, 419], "S3": [420, 629], "S4": [630, 899]}
TITLES = {"S1": "Bienvenue", "S2": "Le service", "S3": "La dégustation", "S4": "Venez / Commandez"}
CROP_BIASES = {"S1": 0.0, "S2": 0.25, "S3": 0.0, "S4": 0.0}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def fraction(value: str) -> float:
    numerator, denominator = value.split("/", 1)
    return float(numerator) / float(denominator)


def capture_file(directory: Path, slot: str) -> Path:
    matches = sorted(path for path in directory.glob(f"{slot}.*") if path.is_file())
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one runtime capture for {slot}, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-job", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--visual-job", type=Path, required=True)
    parser.add_argument("--output-filename", default="VIDEO_T4_RUNTIME_HYBRID_SILENT.mp4")
    args = parser.parse_args()

    job = json.loads(args.render_job.read_text(encoding="utf-8"))
    if job.get("template_id") != "RESTAURATION-T4" or job.get("template_version") != "4.0.0-complete-audio":
        raise SystemExit("Complete T4 RenderJob required")
    if job.get("control_plane") != "cloudflare_worker":
        raise SystemExit("Runtime captures are restricted to the Cloudflare control plane")
    render = job.get("render", {})
    if render.get("visual_mode") != "runtime_hybrid_render" or render.get("runtime_capture_manifest_required") is not True:
        raise SystemExit("RenderJob does not authorize a runtime hybrid visual")
    if render.get("visual_reencode_forbidden") is not False or render.get("audio_mux_video_reencode_forbidden") is not True:
        raise SystemExit("Runtime visual and final mux policies are inconsistent")

    scenes: list[dict[str, Any]] = []
    for slot in DURATIONS:
        capture = job["captures"][slot]
        source = capture_file(args.capture_dir, slot)
        actual_hash = sha256(source)
        if actual_hash != capture["sha256"]:
            raise SystemExit(f"Runtime capture SHA-256 mismatch for {slot}")
        metadata = probe(source)
        video_streams = [stream for stream in metadata["streams"] if stream.get("codec_type") == "video"]
        if len(video_streams) != 1:
            raise SystemExit(f"Runtime capture {slot} must contain exactly one video stream")
        video = video_streams[0]
        duration = float(metadata["format"].get("duration") or video.get("duration") or 0)
        if duration + 0.05 < DURATIONS[slot]:
            raise SystemExit(f"Runtime capture {slot} is too short: {duration:.3f}s")
        rate = fraction(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
        if rate < 12 or rate > 120:
            raise SystemExit(f"Runtime capture {slot} frame rate is unsupported: {rate}")
        if int(video.get("width", 0)) < 320 or int(video.get("height", 0)) < 320:
            raise SystemExit(f"Runtime capture {slot} dimensions are unsupported")
        scenes.append({
            "scene": slot,
            "title": TITLES[slot],
            "duration_seconds": DURATIONS[slot],
            "output_frames": FRAMES[slot],
            "pexels_id": 0,
            "creator": "merchant_runtime_capture",
            "page_url": f"https://runtime.invalid/{job['job_id']}/{slot}",
            "download_url": capture["uri"],
            "cache_filename": source.name,
            "expected_bytes": source.stat().st_size,
            "sha256": actual_hash,
            "source_width": int(video["width"]),
            "source_height": int(video["height"]),
            "source_fps": rate,
            "source_duration_seconds": duration,
            "trim_start_seconds": 0.0,
            "crop_x_bias": CROP_BIASES[slot],
            "content": "merchant-provided runtime capture",
            "demo_fit": f"runtime_{slot.lower()}",
        })

    manifest = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "purpose": "Four SHA-256 verified merchant captures for a runtime T4 hybrid-cinematic render.",
        "license": {
            "provider": "merchant_upload",
            "license_url": None,
            "verified_at_utc": None,
            "summary": "The control-plane client is responsible for upload rights.",
            "raw_media_committed": False,
            "raw_media_published_as_artifact": False,
        },
        "output_contract": {"width": 720, "height": 1280, "fps": 30, "duration_seconds": 30, "total_frames": 900, "audio_streams": 0, "burned_text": False},
        "scenes": scenes,
    }
    visual_job = {
        "schema_version": "3.0.0",
        "job_id": job["job_id"],
        "idempotency_key": job["idempotency_key"],
        "template_id": "RESTAURATION-T4",
        "template_version": "3.0.0",
        "merchant_payload": job["merchant_payload"],
        "output": {"filename": args.output_filename},
        "provenance": {"control_plane": "cloudflare_worker", "render_plane": "github_actions", "source_render_job": str(args.render_job)},
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.visual_job.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.visual_job.write_text(json.dumps(visual_job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "READY", "manifest": str(args.manifest), "visual_job": str(args.visual_job), "captures": {scene["scene"]: scene["sha256"] for scene in scenes}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
