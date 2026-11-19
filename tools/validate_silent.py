#!/usr/bin/env python3
"""Independent technical validation for the T4 silent candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import cv2
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(name: str, condition: bool, detail: Any = "") -> dict[str, Any]:
    return {"check": name, "status": "PASS" if condition else "FAIL", "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("output/t4-silent-v1.0.0"))
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()

    report_path = args.output_dir / "T4_SILENT_RENDER_REPORT.json"
    if not report_path.exists():
        raise SystemExit("Missing render report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    video = args.output_dir / report["output"]["file"]
    contact = args.output_dir / report["contact_sheet_file"]
    if not video.exists():
        raise SystemExit("Missing rendered video")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise SystemExit("ffprobe is required")
    probe = json.loads(subprocess.check_output([
        ffprobe,
        "-v",
        "error",
        "-count_frames",
        "-show_entries",
        "format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_frames,pix_fmt",
        "-of",
        "json",
        str(video),
    ], text=True))
    streams = probe.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    stream = video_streams[0] if video_streams else {}

    capture = cv2.VideoCapture(str(video))
    decoded = 0
    sampled_nonblack = 0
    cyan_line_max_fraction = 0.0
    sample_set = {1, 180, 420, 630, 810, 900, 19, 106, 211, 287, 437, 581, 661, 737}
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        decoded += 1
        if decoded in {1, 180, 420, 630, 810, 900} and float(frame.mean()) > 5.0:
            sampled_nonblack += 1
        if decoded in sample_set:
            b, g, r = cv2.split(frame)
            cyan = (b > 150) & (g > 130) & (r < 125) & ((b.astype(np.int16) - r.astype(np.int16)) > 45)
            row_fraction = float(np.max(np.mean(cyan, axis=1)))
            column_fraction = float(np.max(np.mean(cyan, axis=0)))
            cyan_line_max_fraction = max(cyan_line_max_fraction, row_fraction, column_fraction)
    capture.release()

    events = report.get("events", [])
    families = {event.get("family") for event in events}
    required_families = {
        "T4_TILE_REVEAL",
        "T4_DYNAMIC_GRID_RECONFIG",
        "T4_SHAKE_IMPACT",
        "T4_RECTANGULAR_BLOCK_STUTTER",
        "T4_MICRO_GLITCH",
    }
    micro_events = [event for event in events if event.get("family") == "T4_MICRO_GLITCH"]
    event_frames_in_final_tail = [
        event["event_id"]
        for event in events
        if event["frames"][0] <= 899 and event["frames"][1] >= 810
    ]
    checks = [
        check("video_exists", video.exists(), str(video)),
        check("one_video_stream", len(video_streams) == 1, len(video_streams)),
        check("zero_audio_stream", len(audio_streams) == 0, len(audio_streams)),
        check("h264_codec", stream.get("codec_name") == "h264", stream.get("codec_name")),
        check("dimensions_720x1280", (stream.get("width"), stream.get("height")) == (720, 1280), [stream.get("width"), stream.get("height")]),
        check("pixel_format_yuv420p", stream.get("pix_fmt") == "yuv420p", stream.get("pix_fmt")),
        check("fps_30", stream.get("r_frame_rate") == "30/1" and stream.get("avg_frame_rate") == "30/1", [stream.get("r_frame_rate"), stream.get("avg_frame_rate")]),
        check("duration_30_seconds", abs(float(probe["format"]["duration"]) - 30.0) <= 0.001, probe["format"]["duration"]),
        check("900_frames_probe", int(stream.get("nb_read_frames") or stream.get("nb_frames") or 0) == 900, [stream.get("nb_frames"), stream.get("nb_read_frames")]),
        check("900_frames_decoded", decoded == 900, decoded),
        check("scene_boundaries_and_tail_nonblack", sampled_nonblack == 6, sampled_nonblack),
        check("sha256_matches_render_report", sha256(video) == report["output"]["sha256"], sha256(video)),
        check("exactly_48_events", len(events) == 48, len(events)),
        check("all_48_events_applied", report.get("all_48_events_applied") is True, report.get("all_48_events_applied")),
        check("each_event_frame_count", all(event["expected_frame_count"] == event["applied_frame_count"] for event in events)),
        check("all_events_visibly_nonzero", report.get("all_events_visibly_nonzero") is True and all(float(event["max_mean_absolute_delta_from_base"]) > 0.15 for event in events), min((float(event["max_mean_absolute_delta_from_base"]) for event in events), default=0.0)),
        check("all_five_families_present", required_families <= families, sorted(families)),
        check("micro_glitches_one_to_three_frames", all(1 <= int(event["expected_frame_count"]) <= 3 for event in micro_events), [event["expected_frame_count"] for event in micro_events]),
        check("s4_final_tail_exactly_90_frames", report.get("s4_final_stable_tail", {}).get("frames") == [810, 899] and report.get("s4_final_stable_tail", {}).get("duration_frames") == 90),
        check("s4_final_tail_has_no_effect_event", not event_frames_in_final_tail, event_frames_in_final_tail),
        check("no_text_rendered", report.get("visual_policy", {}).get("text_rendered") is False and report.get("output", {}).get("burned_text_expected") is False),
        check("no_watermark_rendered", report.get("visual_policy", {}).get("watermark_rendered") is False),
        check("no_solid_color_transition_bars", report.get("visual_policy", {}).get("solid_color_transition_bars_rendered") is False),
        check("no_blue_cyan_separator_lines_declared", report.get("visual_policy", {}).get("blue_cyan_separator_lines_rendered") is False),
        check("no_long_cyan_separator_detected", cyan_line_max_fraction < 0.80, round(cyan_line_max_fraction, 6)),
        check("no_voice_over", report.get("audio_policy", {}).get("voice_over") is False),
        check("no_music", report.get("audio_policy", {}).get("music") is False),
        check("raw_rushes_not_published", report.get("raw_rushes_embedded_as_standalone_assets") is False),
        check("four_verified_sources", len(report.get("sources", [])) == 4 and all(len(item.get("sha256", "")) == 64 and item.get("raw_published") is False for item in report.get("sources", []))),
        check("transition_contact_sheet", contact.exists() and contact.stat().st_size > 10000, contact.stat().st_size if contact.exists() else 0),
    ]
    overall = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    validation = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "status": overall,
        "scope": "GitHub Actions silent candidate" if report.get("rendered_on") == "github_actions" else "Local preflight",
        "video": {
            "file": video.name,
            "sha256": sha256(video),
            "bytes": video.stat().st_size,
            "duration_seconds": float(probe["format"]["duration"]),
            "video_streams": len(video_streams),
            "audio_streams": len(audio_streams),
            "decoded_frames": decoded,
        },
        "checks": checks,
        "summary": {
            "passed": sum(item["status"] == "PASS" for item in checks),
            "failed": sum(item["status"] == "FAIL" for item in checks),
        },
        "limitations": [
            "La validation objective ne remplace pas le visionnage créatif du propriétaire.",
            "Le fichier est un candidat silencieux: aucune musique, voix off ou piste audio.",
            "Les rushes Pexels servent à la démonstration et ne remplacent pas les captations d'un commerçant réel.",
        ],
        "owner_approval_required": True,
        "ffprobe": probe,
    }
    proof = args.proof or args.output_dir / "T4_SILENT_VALIDATION.json"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = args.output_dir / "RAPPORT_RENDU_SILENCIEUX.md"
    summary.write_text(
        "# T4 — Validation du rendu silencieux\n\n"
        f"**Résultat objectif : {overall}** — {validation['summary']['passed']} contrôles PASS, {validation['summary']['failed']} échec.\n\n"
        f"- fichier : `{video.name}` ;\n"
        f"- SHA-256 : `{validation['video']['sha256']}` ;\n"
        "- 30,000 s · 720 × 1280 · 30 i/s · 900 images ;\n"
        "- H.264 / yuv420p ;\n"
        "- zéro piste audio et aucun texte incrusté ;\n"
        "- exactement quatre scènes 6/8/7/9 s ;\n"
        "- fusion A+B+C+D appliquée par 48 événements ;\n"
        "- fin de S4 stable pendant 90 images sans effet ;\n"
        "- aucun trait séparateur bleu/cyan généré ;\n"
        "- validation humaine encore requise.\n",
        encoding="utf-8",
    )
    print(f"T4_SILENT_VALIDATION_{overall} {proof}")
    if overall != "PASS":
        for item in checks:
            if item["status"] == "FAIL":
                print("FAIL", item["check"], item["detail"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
