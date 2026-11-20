#!/usr/bin/env python3
"""Normalize the four owner-approved T4 clips and build a 30 s voice stem."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SR = 48_000
TOTAL_S = 30.0
N = int(SR * TOTAL_S)


def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def loudness(path: Path, target_i: float, target_tp: float) -> dict[str, Any]:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
        "-af", f"loudnorm=I={target_i}:TP={target_tp}:LRA=7:print_format=json",
        "-f", "null", "-",
    ], capture_output=True, text=True)
    blocks = re.findall(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    if not blocks:
        raise RuntimeError(f"No loudness measurement for {path}")
    return json.loads(blocks[-1])


def normalize(source: Path, target: Path, target_i: float, target_tp: float) -> dict[str, Any]:
    before = loudness(source, target_i, target_tp)
    gain_db = target_i - float(before["input_i"])
    limit = 10 ** ((target_tp - 0.1) / 20.0)
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source), "-map", "0:a:0",
        "-af", (
            f"afade=t=in:st=0:d=0.006,volume={gain_db:.6f}dB,"
            f"alimiter=limit={limit:.9f}:attack=5:release=50:level=false:latency=true"
        ),
        "-ar", str(SR), "-ac", "1", "-map_metadata", "-1", "-c:a", "pcm_s16le", str(target),
    ])
    after = loudness(target, target_i, target_tp)
    return {
        "applied_gain_db": round(gain_db, 3),
        "integrated_lufs": float(after["input_i"]),
        "true_peak_dbtp": float(after["input_tp"]),
        "loudness_range_lu": float(after["input_lra"]),
    }


def decode_mono(path: Path) -> np.ndarray:
    raw = run([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
        "-ar", str(SR), "-ac", "1", "-f", "f32le", "-",
    ], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def write_wav(path: Path, data: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR),
        "-ac", "1", "-i", "-", "-map_metadata", "-1", "-c:a", "pcm_s24le", str(path),
    ], stdin=subprocess.PIPE)
    process.communicate(np.asarray(data, dtype="<f4").tobytes())
    if process.returncode:
        raise RuntimeError(f"Cannot write {path}")


def probe(path: Path) -> dict[str, Any]:
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_name,sample_rate,channels",
        "-of", "json", str(path),
    ], capture_output=True, text=True).stdout)


def sample_qc(audio: np.ndarray) -> dict[str, Any]:
    peak = float(np.max(np.abs(audio)))
    return {
        "sample_peak_dbfs": round(20 * math.log10(max(peak, 1e-12)), 3),
        "clipped_sample_count": int(np.count_nonzero(np.abs(audio) >= 0.999999)),
        "nan_count": int(np.isnan(audio).sum()),
        "inf_count": int(np.isinf(audio).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config/T4_VOICE_MIX_V1_0_0.json")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    voice = config["voice"]
    if voice["candidate"] != "VOIX-B" or voice["voice_id"] != "voice-07":
        raise RuntimeError("The owner-approved T4 voice must be VOIX-B / voice-07")
    clips_config = voice["clips"]
    if len(clips_config) != 4 or [item["scene"] for item in clips_config] != [1, 2, 3, 4]:
        raise RuntimeError("Exactly four ordered T4 voice clips are required")
    if [float(item["start_s"]) for item in clips_config] != [1.2, 6.8, 14.7, 21.8]:
        raise RuntimeError("T4 voice placements must follow the approved T1/T3 model")

    target_i = float(voice["normalization_target_lufs"])
    target_tp = float(voice["normalization_true_peak_dbtp_max"])
    tolerance = float(voice["normalization_tolerance_lu"])
    stem = np.zeros(N, dtype=np.float64)
    rows: list[dict[str, Any]] = []

    for item in clips_config:
        source = ROOT / item["source"]
        processed = ROOT / item["processed"]
        if not source.is_file() or sha256(source) != item["source_sha256"]:
            raise RuntimeError(f"Voice source integrity failure: {source}")
        stats = normalize(source, processed, target_i, target_tp)
        if not target_i - tolerance <= stats["integrated_lufs"] <= target_i + tolerance:
            raise RuntimeError(f"Voice loudness outside tolerance: {processed}")
        if stats["true_peak_dbtp"] > target_tp:
            raise RuntimeError(f"Voice true peak above ceiling: {processed}")
        clip = decode_mono(processed)
        start_s = float(item["start_s"])
        start = int(round(start_s * SR))
        end = start + len(clip)
        scene_start, scene_end = map(float, item["scene_window_s"])
        end_s = end / SR
        if start_s < scene_start or end_s > scene_end:
            raise RuntimeError(f"Voice clip exceeds scene {item['scene']}: {start_s:.3f}–{end_s:.3f}")
        stem[start:end] += clip
        media = probe(processed)
        rows.append({
            **item,
            "end_s": round(end_s, 6),
            "duration_s": round(len(clip) / SR, 6),
            "decoded_samples": len(clip),
            "processed_sha256": sha256(processed),
            "normalization": stats,
            "probe": media,
        })

    stem_path = ROOT / voice["stem_file"]
    write_wav(stem_path, stem)
    decoded_stem = decode_mono(stem_path)
    if len(decoded_stem) != N:
        raise RuntimeError(f"Stem must contain exactly {N} samples")
    stem_stats = loudness(stem_path, target_i, target_tp)
    manifest = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "status": "PASS",
        "generated_on": "2026-11-20",
        "generated_plane": "github_actions" if os.environ.get("GITHUB_ACTIONS") == "true" else "local_preflight",
        "config": str(args.config.relative_to(ROOT)),
        "provider": voice["provider"],
        "candidate": voice["candidate"],
        "voice_id": voice["voice_id"],
        "approval": voice["approval"],
        "language": voice["language"],
        "retimed": False,
        "clips": rows,
        "stem": {
            "file": voice["stem_file"],
            "sha256": sha256(stem_path),
            "bytes": stem_path.stat().st_size,
            "decoded_samples": len(decoded_stem),
            "duration_s": len(decoded_stem) / SR,
            "sample_rate_hz": SR,
            "channels": 1,
            "integrated_lufs": float(stem_stats["input_i"]),
            "true_peak_dbtp": float(stem_stats["input_tp"]),
            **sample_qc(decoded_stem),
        },
    }
    package = stem_path.parent
    manifest_path = package / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = [*(ROOT / item["source"] for item in clips_config), *(ROOT / item["processed"] for item in clips_config), stem_path, manifest_path]
    (package / "SHA256SUMS.txt").write_text("".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in files), encoding="utf-8")
    print(json.dumps({"status":"PASS","clips":len(rows),"stem":voice["stem_file"],"sha256":sha256(stem_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
