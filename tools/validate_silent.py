#!/usr/bin/env python3
"""Independent validation for the T4 V2 natural-transition candidate."""
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

EXPECTED_CUTS = [180, 420, 630]
EXPECTED_WINDOWS = [[180, 183], [420, 423], [630, 633]]


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
    parser.add_argument("--output-dir", type=Path, default=Path("output/t4-natural-v2.0.0"))
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
    sample_set = {1, 180, 181, 184, 420, 421, 424, 630, 631, 634, 810, 900}
    nonblack_set = {1, 180, 420, 630, 810, 900}
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        decoded += 1
        if decoded in nonblack_set and float(frame.mean()) > 5.0:
            sampled_nonblack += 1
        if decoded in sample_set:
            b, g, r = cv2.split(frame)
            cyan = (b > 150) & (g > 130) & (r < 125) & ((b.astype(np.int16) - r.astype(np.int16)) > 45)
            row_fraction = float(np.max(np.mean(cyan, axis=1)))
            column_fraction = float(np.max(np.mean(cyan, axis=0)))
            cyan_line_max_fraction = max(cyan_line_max_fraction, row_fraction, column_fraction)
    capture.release()

    events = report.get("events", [])
    style = report.get("transition_style", {})
    retired = report.get("retired_v1_effects", {})
    stable = report.get("stable_full_frame_audit", {})
    event_frames_in_final_tail = [
        event["event_id"]
        for event in events
        if event["frames"][0] <= 899 and event["frames"][1] >= 810
    ]
    old_families = {
        "T4_TILE_REVEAL",
        "T4_DYNAMIC_GRID_RECONFIG",
        "T4_SHAKE_IMPACT",
        "T4_RECTANGULAR_BLOCK_STUTTER",
        "T4_MICRO_GLITCH",
    }
    event_families = {event.get("family") for event in events}
    checks = [
        check("video_exists", video.exists(), str(video)),
        check("report_schema_v2", report.get("schema_version") == "2.0.0", report.get("schema_version")),
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
        check("exactly_three_transitions", len(events) == 3, len(events)),
        check("transitions_only_at_cut_frames", [event.get("cut_frame") for event in events] == EXPECTED_CUTS, [event.get("cut_frame") for event in events]),
        check("exact_transition_windows", [event.get("frames") for event in events] == EXPECTED_WINDOWS, [event.get("frames") for event in events]),
        check("maximum_four_frames_each", all(int(event.get("expected_frame_count", 99)) <= 4 for event in events), [event.get("expected_frame_count") for event in events]),
        check("natural_speed_cut_family_only", event_families == {"T4_NATURAL_SPEED_CUT"}, sorted(str(item) for item in event_families)),
        check("no_legacy_effect_family", not (event_families & old_families), sorted(event_families & old_families)),
        check("all_three_transitions_applied", report.get("all_3_boundary_transitions_applied") is True, report.get("all_3_boundary_transitions_applied")),
        check("each_transition_frame_count", all(event["expected_frame_count"] == event["applied_frame_count"] for event in events)),
        check("each_transition_visibly_nonzero", report.get("all_events_visibly_nonzero") is True and all(float(event["max_mean_absolute_delta_from_incoming_base"]) > 0.15 for event in events), min((float(event["max_mean_absolute_delta_from_incoming_base"]) for event in events), default=0.0)),
        check("transition_style_boundary_only", style.get("transitions_only_at_rush_changes") is True and style.get("cut_frames") == EXPECTED_CUTS),
        check("transition_style_full_frame_only", style.get("full_frame_only") is True),
        check("stable_full_frame_share_at_least_98_percent", float(stable.get("stable_full_frame_share", 0)) >= 0.98, stable.get("stable_full_frame_share")),
        check("exactly_888_stable_frames", stable.get("stable_full_frame_frames") == 888 and stable.get("transition_frames") == 12, stable),
        check("zero_events_outside_rush_changes", stable.get("events_outside_rush_changes") == 0, stable.get("events_outside_rush_changes")),
        check("all_exaggerated_v1_effects_disabled", retired and all(value is False for value in retired.values()), retired),
        check("s4_final_tail_exactly_90_frames", report.get("s4_final_stable_tail", {}).get("frames") == [810, 899] and report.get("s4_final_stable_tail", {}).get("duration_frames") == 90),
        check("s4_final_tail_has_no_transition", not event_frames_in_final_tail, event_frames_in_final_tail),
        check("no_text_rendered", report.get("visual_policy", {}).get("text_rendered") is False and report.get("output", {}).get("burned_text_expected") is False),
        check("no_watermark_rendered", report.get("visual_policy", {}).get("watermark_rendered") is False),
        check("no_mosaic_or_grid_rendered", report.get("visual_policy", {}).get("mosaic_or_grid_rendered") is False),
        check("no_shake_or_glitch_rendered", report.get("visual_policy", {}).get("shake_or_glitch_rendered") is False),
        check("no_solid_color_transition_bars", report.get("visual_policy", {}).get("solid_color_transition_bars_rendered") is False),
        check("no_blue_cyan_separator_lines_declared", report.get("visual_policy", {}).get("blue_cyan_separator_lines_rendered") is False),
        check("no_long_cyan_separator_detected", cyan_line_max_fraction < 0.80, round(cyan_line_max_fraction, 6)),
        check("no_voice_over", report.get("audio_policy", {}).get("voice_over") is False),
        check("no_music", report.get("audio_policy", {}).get("music") is False),
        check("raw_rushes_not_published", report.get("raw_rushes_embedded_as_standalone_assets") is False),
        check("four_verified_sources", len(report.get("sources", [])) == 4 and all(len(item.get("sha256", "")) == 64 and item.get("raw_published") is False for item in report.get("sources", []))),
        check("natural_transition_contact_sheet", contact.exists() and contact.stat().st_size > 10000, contact.stat().st_size if contact.exists() else 0),
    ]
    overall = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    validation = {
        "schema_version": "2.0.0",
        "template_id": "RESTAURATION-T4",
        "status": overall,
        "scope": "GitHub Actions V2 natural-transition candidate" if report.get("rendered_on") == "github_actions" else "Local V2 preflight",
        "video": {
            "file": video.name,
            "sha256": sha256(video),
            "bytes": video.stat().st_size,
            "duration_seconds": float(probe["format"]["duration"]),
            "video_streams": len(video_streams),
            "audio_streams": len(audio_streams),
            "decoded_frames": decoded,
        },
        "natural_transition_audit": {
            "count": len(events),
            "cut_frames": [event.get("cut_frame") for event in events],
            "windows": [event.get("frames") for event in events],
            "stable_full_frame_share": stable.get("stable_full_frame_share"),
            "legacy_effects_active": sorted(event_families & old_families),
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
    proof = args.proof or args.output_dir / "T4_NATURAL_VALIDATION_V2.json"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = args.output_dir / "RAPPORT_TRANSITIONS_NATURELLES_V2.md"
    summary.write_text(
        "# T4 V2 — Validation des transitions naturelles\n\n"
        f"**Résultat objectif : {overall}** — {validation['summary']['passed']} contrôles PASS, {validation['summary']['failed']} échec.\n\n"
        f"- fichier : `{video.name}` ;\n"
        f"- SHA-256 : `{validation['video']['sha256']}` ;\n"
        "- 30,000 s · 720 × 1280 · 30 i/s · 900 images ;\n"
        "- H.264 / yuv420p ; zéro piste audio ; aucun texte incrusté ;\n"
        "- exactement trois raccords rapides de quatre images aux secondes 6, 14 et 21 ;\n"
        "- aucun raccord au milieu d'un rush ;\n"
        "- aucune mosaïque, grille, secousse, glitch ou cassure rectangulaire ;\n"
        "- 888 images plein écran sans transition, soit 98,67 % du montage ;\n"
        "- fin de S4 stable pendant 90 images ;\n"
        "- validation humaine encore requise.\n",
        encoding="utf-8",
    )
    print(f"T4_NATURAL_VALIDATION_{overall} {proof}")
    if overall != "PASS":
        for item in checks:
            if item["status"] == "FAIL":
                print("FAIL", item["check"], item["detail"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
