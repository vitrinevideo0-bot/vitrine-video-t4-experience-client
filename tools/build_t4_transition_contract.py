#!/usr/bin/env python3
"""Build the owner-selected T4 V3 hybrid cinematic transition timeline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS = 30
TOTAL = 900
TRANSITION_FRAMES = 8

SIGNATURES = (
    {
        "event_id": "T4-V3-CUT-01",
        "family": "T4_CINEMATIC_WHIP_PAN",
        "variant": "fast_horizontal_whip_to_service",
        "outgoing_scene_id": "S1",
        "incoming_scene_id": "S2",
        "cut_frame": 180,
        "direction": "left",
    },
    {
        "event_id": "T4-V3-CUT-02",
        "family": "T4_CINEMATIC_ZOOM_MATCH",
        "variant": "plate_to_tasting_zoom_through",
        "outgoing_scene_id": "S2",
        "incoming_scene_id": "S3",
        "cut_frame": 420,
        "direction": "inward",
    },
    {
        "event_id": "T4-V3-CUT-03",
        "family": "T4_CINEMATIC_WHIP_ZOOM",
        "variant": "portrait_to_ambience_opening",
        "outgoing_scene_id": "S3",
        "incoming_scene_id": "S4",
        "cut_frame": 630,
        "direction": "left_and_out",
    },
)


def build() -> dict:
    events = []
    for signature in SIGNATURES:
        cut = signature["cut_frame"]
        start = cut - 4
        end = cut + 3
        event = dict(signature)
        event.update({
            "frames": [start, end],
            "cut_seconds_exact": round(cut / FPS, 6),
            "start_seconds_exact": round(start / FPS, 6),
            "end_seconds_exclusive_exact": round((end + 1) / FPS, 6),
            "duration_frames": TRANSITION_FRAMES,
            "duration_seconds": round(TRANSITION_FRAMES / FPS, 6),
            "full_frame_only": True,
            "clean_endpoint_frames_required": True,
        })
        events.append(event)

    covered = sum(event["duration_frames"] for event in events)
    stable = TOTAL - covered
    return {
        "schema_version": "3.0.0",
        "template_id": "RESTAURATION-T4",
        "title": "Transitions hybrides cinématiques — trois changements de rush",
        "status": "owner_selected_hybrid_candidate_pending_review",
        "owner_choice": "approvals/CHOIX_TRANSITIONS_HYBRIDES_V3_2026-11-18.json",
        "superseded_candidates": [
            {
                "version": "v1",
                "verdict": "too_exaggerated",
                "reason": "Effets trop nombreux à l'intérieur des rushes."
            },
            {
                "version": "v2",
                "verdict": "too_basic",
                "reason": "Fondus rapides trop discrets pour marquer le changement de rush."
            }
        ],
        "truth_model": {
            "OWNER_SELECTED": "Option Hybride cinématique explicitement choisie par le propriétaire.",
            "ENGINE_DECISION": "Chaque signature dure huit images centrées sur la coupe, utilise uniquement des transformations plein écran et se termine exactement sur le rush entrant.",
            "rule": "Impressionnant au changement de rush, totalement stable en dehors des trois fenêtres."
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
            "transitions_only_around_rush_changes_required": True,
            "full_frame_between_transition_windows_required": True,
            "three_distinct_cinematic_signatures_required": True,
            "transition_duration_frames": TRANSITION_FRAMES,
            "clean_landing_on_incoming_rush_required": True,
            "mosaic_forbidden": True,
            "dynamic_grid_forbidden": True,
            "multi_panel_forbidden": True,
            "glitch_forbidden": True,
            "rgb_split_forbidden": True,
            "rectangular_block_stutter_forbidden": True,
            "solid_color_transition_bars_forbidden": True,
            "blue_or_cyan_separator_lines_forbidden": True,
            "silent_render_text_forbidden": True,
            "silent_render_audio_forbidden": True,
            "s4_final_stable_tail_frames": 90
        },
        "transition_parameter_profiles": {
            "T4_CINEMATIC_WHIP_PAN": {
                "truth": "ENGINE_DECISION",
                "duration_frames": 8,
                "full_frame_only": True,
                "maximum_horizontal_translation_px": 110,
                "maximum_horizontal_blur_kernel_px": 41,
                "maximum_scale": 1.035,
                "rotation_degrees": 0,
                "blend_curve": "concentrated_smoothstep",
                "endpoint_frames_clean": True
            },
            "T4_CINEMATIC_ZOOM_MATCH": {
                "truth": "ENGINE_DECISION",
                "duration_frames": 8,
                "full_frame_only": True,
                "outgoing_zoom_center_normalized": [0.52, 0.57],
                "incoming_zoom_center_normalized": [0.52, 0.34],
                "maximum_outgoing_scale": 1.34,
                "maximum_incoming_entry_scale": 1.22,
                "radial_zoom_blur_samples": 4,
                "flash": False,
                "endpoint_frames_clean": True
            },
            "T4_CINEMATIC_WHIP_ZOOM": {
                "truth": "ENGINE_DECISION",
                "duration_frames": 8,
                "full_frame_only": True,
                "maximum_horizontal_translation_px": 72,
                "maximum_horizontal_blur_kernel_px": 31,
                "maximum_outgoing_scale": 1.16,
                "incoming_entry_scale": 1.24,
                "incoming_landing_scale": 1.0,
                "rotation_degrees": 0,
                "endpoint_frames_clean": True
            }
        },
        "stable_windows": [
            {"frames": [0, 175], "reason": "S1 naturel avant le whip-pan."},
            {"frames": [184, 415], "reason": "S2 naturel entre les raccords."},
            {"frames": [424, 625], "reason": "S3 naturel entre les raccords."},
            {"frames": [634, 899], "reason": "S4 naturel après le whip-zoom, avec fin stable de trois secondes."}
        ],
        "cadence_audit": {
            "total_events": len(events),
            "rush_change_count": 3,
            "events_outside_rush_change_windows": 0,
            "covered_transition_frames": covered,
            "stable_full_frame_frames": stable,
            "stable_full_frame_share": round(stable / TOTAL, 6),
            "transition_share": round(covered / TOTAL, 6),
            "event_duration_frames": TRANSITION_FRAMES,
            "distinct_transition_family_count": len({event["family"] for event in events})
        },
        "timeline_events": events
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reverse-engineering/T4_TRANSITIONS_HYBRIDES_30S_V3.json")
    args = parser.parse_args()
    contract = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"T4_HYBRID_TRANSITION_CONTRACT_BUILT {len(contract['timeline_events'])} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
