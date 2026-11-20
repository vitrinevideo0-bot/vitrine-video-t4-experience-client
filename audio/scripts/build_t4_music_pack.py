#!/usr/bin/env python3
"""Build four hash-locked 30 s T4 Afrobeat derivatives from official sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SR = 48_000
TOTAL_S = 30.0
N = int(SR * TOTAL_S)


def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    print("RUN", " ".join(command), flush=True)
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


def decode_stereo(path: Path) -> np.ndarray:
    raw = run([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-t", str(TOTAL_S),
        "-ar", str(SR), "-ac", "2", "-f", "f32le", "-",
    ], capture_output=True).stdout
    data = np.frombuffer(raw, dtype="<f4").astype(np.float64)
    return data.reshape(-1, 2)


def probe(path: Path) -> dict[str, Any]:
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels",
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
    parser.add_argument("--manifest", type=Path, default=ROOT / "audio/music/t4-afrobeat-v1/source_manifest.json")
    parser.add_argument("--source-cache", type=Path, default=Path.home() / ".cache/t4-music-originals")
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    tracks = data["tracks"]
    if len(tracks) != 4 or [track["choice"] for track in tracks] != ["1", "2", "3", "4"]:
        raise RuntimeError("T4 requires exactly the four owner-approved choices 1/2/3/4")
    if [track["pixabay_id"] for track in tracks] != [260354, 154868, 162186, 321930]:
        raise RuntimeError("Unexpected T4 Pixabay source set")
    if not all(track["owner_approved"] and track["production_eligible"] for track in tracks):
        raise RuntimeError("Every T4 music source must be owner-approved and production-eligible")
    if not all(track["content_id_registered"] is False for track in tracks):
        raise RuntimeError("The replacement pool must have no Content ID Registered label in its dated evidence")
    if not all(track["claim_management_required"] is False and track["never_register_in_content_id"] is True for track in tracks):
        raise RuntimeError("The replacement pool must forbid project Content ID registration")

    report_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="t4-music-build-") as temp_name:
        temp = Path(temp_name)
        for track in tracks:
            source = args.source_cache / track["source"]["cache_filename"]
            if not source.is_file() or sha256(source) != track["source"]["sha256"]:
                raise RuntimeError(f"Official source integrity failure: {source}")
            derivative = track["derivative"]
            output = ROOT / derivative["file"]
            output.parent.mkdir(parents=True, exist_ok=True)
            trimmed = temp / f"{track['id']}_trimmed.wav"
            start = float(derivative["source_start_s"])
            fade_in = float(derivative["fade_in_s"])
            fade_out_start = float(derivative["fade_out_start_s"])
            fade_out = float(derivative["fade_out_s"])
            run([
                "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.6f}", "-i", str(source),
                "-af", (
                    f"atrim=duration={TOTAL_S},asetpts=PTS-STARTPTS,"
                    f"afade=t=in:st=0:d={fade_in},"
                    f"afade=t=out:st={fade_out_start}:d={fade_out},"
                    f"apad=whole_dur={TOTAL_S}"
                ),
                "-t", str(TOTAL_S), "-ar", str(SR), "-ac", "2", "-map_metadata", "-1",
                "-c:a", "pcm_f32le", str(trimmed),
            ])
            target_i = float(derivative["target_integrated_lufs"])
            target_tp = float(derivative["target_true_peak_dbtp"])
            first = loudness(trimmed, target_i, target_tp)
            audio_filter = (
                f"loudnorm=I={target_i}:TP={target_tp}:LRA=7:"
                f"measured_I={first['input_i']}:measured_LRA={first['input_lra']}:"
                f"measured_TP={first['input_tp']}:measured_thresh={first['input_thresh']}:"
                f"offset={first['target_offset']}:linear=false:print_format=summary"
            )
            run([
                "ffmpeg", "-y", "-v", "error", "-i", str(trimmed), "-map", "0:a:0",
                "-af", audio_filter, "-t", str(TOTAL_S), "-ar", str(SR), "-ac", "2",
                "-map_metadata", "-1", "-c:a", "libmp3lame", "-b:a", f"{int(derivative['bitrate_kbps'])}k",
                "-write_xing", "1", str(output),
            ])
            audio = decode_stereo(output)
            measured = loudness(output, target_i, target_tp)
            media = probe(output)
            qc = sample_qc(audio)
            checks = {
                "decoded_samples_exact": len(audio) == N,
                "duration_exact": abs(len(audio) / SR - TOTAL_S) <= 0.001,
                "integrated_loudness": -17.7 <= float(measured["input_i"]) <= -16.3,
                "true_peak": float(measured["input_tp"]) <= -0.7,
                "stereo_48khz": int(media["streams"][0]["sample_rate"]) == SR and int(media["streams"][0]["channels"]) == 2,
                "no_clipping": qc["clipped_sample_count"] == 0,
                "finite_samples": qc["nan_count"] == 0 and qc["inf_count"] == 0,
            }
            if not all(checks.values()):
                raise RuntimeError(f"T4 music derivative QC failed for {output}: {checks}")
            actual = {
                "file": derivative["file"], "sha256": sha256(output), "bytes": output.stat().st_size,
                "decoded_samples": len(audio), "decoded_duration_s": len(audio) / SR,
                "container_duration_s": float(media["format"]["duration"]),
                "sample_rate_hz": int(media["streams"][0]["sample_rate"]),
                "channels": int(media["streams"][0]["channels"]),
                "integrated_lufs": float(measured["input_i"]),
                "true_peak_dbtp": float(measured["input_tp"]), **qc,
            }
            derivative["built"] = actual
            report_rows.append({
                "choice": track["choice"], "id": track["id"], "pixabay_id": track["pixabay_id"],
                "title": track["title"], "artist": track["artist"],
                "source_sha256": track["source"]["sha256"], "derivative": actual,
                "checks": [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()],
            })

    args.manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    package = args.manifest.resolve().parent
    report = {
        "schema_version": "1.0.0", "template_id": "RESTAURATION-T4", "status": "PASS",
        "generated_on": "2026-11-18", "track_count": 4,
        "original_full_tracks_committed": False,
        "derivatives": report_rows,
        "summary": {"passed": sum(len(row["checks"]) for row in report_rows), "failed": 0},
    }
    report_path = package / "BUILD_PROVENANCE.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sums = sorted(
        path for path in package.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (package / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(package)}\n" for path in sums), encoding="utf-8"
    )
    print(json.dumps({"status":"PASS","track_count":4,"derivatives":[row["derivative"] for row in report_rows]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
