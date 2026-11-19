#!/usr/bin/env python3
"""Build the owner-corrected T4 natural transition timeline.

V2 deliberately contains only three short transitions: one at each real rush
change. No decorative effect is allowed inside a shot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS = 30
TOTAL = 900
CUTS = (
    ("T4-NAT-CUT-01", "S1", "S2", 180, "horizontal"),
    ("T4-NAT-CUT-02", "S2", "S3", 420, "vertical"),
    ("T4-NAT-CUT-03", "S3", "S4", 630, "horizontal"),
)
TRANSITION_FRAMES = 4


def build() -> dict:
    events = []
    for event_id, outgoing, incoming, cut_frame, blur_axis in CUTS:
        start = cut_frame
        end = cut_frame + TRANSITION_FRAMES - 1
        events.append({
            "event_id": event_id,
            "family": "T4_NATURAL_SPEED_CUT",
            "variant": "fast_soft_motion_dissolve",
            "outgoing_scene_id": outgoing,
            "incoming_scene_id": incoming,
            "cut_frame": cut_frame,
            "cut_seconds_exact": round(cut_frame / FPS, 6),
            "frames": [start, end],
            "start_seconds_exact": round(start / FPS, 6),
            "end_seconds_exclusive_exact": round((end + 1) / FPS, 6),
            "duration_frames": TRANSITION_FRAMES,
            "duration_seconds": round(TRANSITION_FRAMES / FPS, 6),
            "blur_axis": blur_axis,
            "full_frame_only": True,
        })

    covered = sum(event["duration_frames"] for event in events)
    stable = TOTAL - covered
    return {
        "schema_version": "2.0.0",
        "template_id": "RESTAURATION-T4",
        "title": "Transitions naturelles rapides — uniquement aux changements de rush",
        "status": "owner_corrected_candidate_pending_review",
        "owner_correction": "approvals/CORRECTION_TRANSITIONS_NATURELLES_V2_2026-11-18.json",
        "superseded_candidate": {
            "version": "v1",
            "reason": "Transitions jugées trop exagérées par le propriétaire.",
            "retired_event_count": 48,
            "retired_families": [
                "T4_TILE_REVEAL",
                "T4_DYNAMIC_GRID_RECONFIG",
                "T4_SHAKE_IMPACT",
                "T4_RECTANGULAR_BLOCK_STUTTER",
                "T4_MICRO_GLITCH"
            ]
        },
        "truth_model": {
            "OWNER_DIRECTED": "Les transitions doivent être naturelles, rapides et réservées aux changements de rush.",
            "ENGINE_DECISION": "Un raccord plein écran de quatre images utilise un fondu de mouvement très léger, sans translation, zoom, rotation ni élément graphique.",
            "rule": "Le rush demeure intact et plein écran en dehors des trois fenêtres de raccord."
        },
        "format_contract": {
            "orientation": "portrait",
            "aspect_ratio": "9:16",
            "width": 720,
            "height": 1280,
            "fps": FPS,
            "total_frames": TOTAL,
            "duration_seconds": 30,
            "scene_boundaries_frames": [0, 180, 420, 630, 900],
            "rush_change_frames": [180, 420, 630],
            "scene_durations_seconds": [6, 8, 7, 9],
            "scene_frame_ranges_inclusive": {
                "S1": [0, 179],
                "S2": [180, 419],
                "S3": [420, 629],
                "S4": [630, 899]
            }
        },
        "owner_constraints": {
            "transitions_only_at_rush_changes_required": True,
            "full_frame_between_cuts_required": True,
            "maximum_transition_duration_frames": TRANSITION_FRAMES,
            "mosaic_forbidden": True,
            "dynamic_grid_forbidden": True,
            "shake_forbidden": True,
            "glitch_forbidden": True,
            "rectangular_block_stutter_forbidden": True,
            "solid_color_transition_bars_forbidden": True,
            "blue_or_cyan_separator_lines_forbidden": True,
            "silent_render_text_forbidden": True,
            "silent_render_audio_forbidden": True,
            "s4_final_stable_tail_frames": 90
        },
        "transition_parameter_profiles": {
            "T4_NATURAL_SPEED_CUT": {
                "truth": "ENGINE_DECISION",
                "duration_frames": TRANSITION_FRAMES,
                "duration_milliseconds": round(1000 * TRANSITION_FRAMES / FPS, 3),
                "blend_curve": "smoothstep",
                "maximum_motion_blur_kernel_px": 5,
                "translation_px": 0,
                "rotation_degrees": 0,
                "scale": 1.0,
                "crop_change": False,
                "panels": 1,
                "full_frame_only": True,
                "flash": False,
                "color_overlay": False
            }
        },
        "protected_stable_windows": [
            {
                "frames": [0, 179],
                "reason": "S1 reste intact jusqu'au changement de rush."
            },
            {
                "frames": [184, 419],
                "reason": "S2 reste intact après son raccord d'entrée."
            },
            {
                "frames": [424, 629],
                "reason": "S3 reste intact après son raccord d'entrée."
            },
            {
                "frames": [634, 899],
                "reason": "S4 reste intact après son raccord d'entrée, dont les trois dernières secondes."
            }
        ],
        "cadence_audit": {
            "total_events": len(events),
            "rush_change_count": 3,
            "events_outside_rush_changes": 0,
            "covered_transition_frames": covered,
            "stable_full_frame_frames": stable,
            "stable_full_frame_share": round(stable / TOTAL, 6),
            "transition_share": round(covered / TOTAL, 6),
            "maximum_event_duration_frames": TRANSITION_FRAMES
        },
        "timeline_events": events
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reverse-engineering/T4_TRANSITIONS_NATURELLES_30S_V2.json")
    args = parser.parse_args()
    contract = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"T4_NATURAL_TRANSITION_CONTRACT_BUILT {len(contract['timeline_events'])} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
