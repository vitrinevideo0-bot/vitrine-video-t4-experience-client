#!/usr/bin/env python3
"""Build the deterministic 30-second T4 transition timeline from the approved A+B+C+D grammar."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS = 30
TOTAL = 900

SCHEDULE = {
    "S1": [
        (0, 14, "T4_TILE_REVEAL", "future_windows_open", 11),
        (18, 33, "T4_DYNAMIC_GRID_RECONFIG", "central_dominant", 12),
        (38, 39, "T4_MICRO_GLITCH", "slices_rgb", 13),
        (50, 57, "T4_RECTANGULAR_BLOCK_STUTTER", "horizontal_media_blocks", 14),
        (60, 63, "T4_SHAKE_IMPACT", "damped_impact", 15),
        (74, 87, "T4_TILE_REVEAL", "staggered_mosaic", 16),
        (92, 93, "T4_MICRO_GLITCH", "thin_slices", 17),
        (105, 122, "T4_DYNAMIC_GRID_RECONFIG", "three_columns", 18),
        (127, 128, "T4_MICRO_GLITCH", "rgb_offset", 19),
        (140, 153, "T4_TILE_REVEAL", "checker_reveal", 20),
        (159, 162, "T4_SHAKE_IMPACT", "damped_impact", 21),
        (171, 172, "T4_MICRO_GLITCH", "slices_rgb", 22),
    ],
    "S2": [
        (180, 194, "T4_TILE_REVEAL", "previous_scene_to_current", 31),
        (198, 201, "T4_SHAKE_IMPACT", "damped_impact", 32),
        (210, 227, "T4_DYNAMIC_GRID_RECONFIG", "offset_2x2", 33),
        (232, 233, "T4_MICRO_GLITCH", "slices_rgb", 34),
        (244, 251, "T4_RECTANGULAR_BLOCK_STUTTER", "horizontal_media_blocks", 35),
        (254, 267, "T4_TILE_REVEAL", "staggered_mosaic", 36),
        (272, 275, "T4_SHAKE_IMPACT", "damped_impact", 37),
        (286, 303, "T4_DYNAMIC_GRID_RECONFIG", "central_dominant", 38),
        (308, 310, "T4_MICRO_GLITCH", "thin_slices", 39),
        (320, 334, "T4_TILE_REVEAL", "checker_reveal", 40),
        (339, 346, "T4_RECTANGULAR_BLOCK_STUTTER", "horizontal_media_blocks", 41),
        (349, 352, "T4_SHAKE_IMPACT", "damped_impact", 42),
        (363, 380, "T4_DYNAMIC_GRID_RECONFIG", "three_columns", 43),
        (385, 386, "T4_MICRO_GLITCH", "rgb_offset", 44),
        (398, 415, "T4_TILE_REVEAL", "staggered_mosaic", 45),
    ],
    "S3": [
        (420, 431, "T4_TILE_REVEAL", "previous_scene_to_current", 51),
        (436, 449, "T4_DYNAMIC_GRID_RECONFIG", "face_safe_satellites", 52),
        (454, 455, "T4_MICRO_GLITCH", "face_safe_slices", 53),
        (464, 466, "T4_SHAKE_IMPACT", "face_safe_impact", 54),
        (549, 562, "T4_TILE_REVEAL", "face_safe_mosaic", 55),
        (567, 568, "T4_MICRO_GLITCH", "face_safe_slices", 56),
        (580, 593, "T4_DYNAMIC_GRID_RECONFIG", "face_safe_satellites", 57),
        (598, 600, "T4_SHAKE_IMPACT", "face_safe_impact", 58),
        (610, 611, "T4_MICRO_GLITCH", "face_safe_slices", 59),
    ],
    "S4": [
        (630, 644, "T4_TILE_REVEAL", "previous_scene_to_current", 71),
        (648, 651, "T4_SHAKE_IMPACT", "damped_impact", 72),
        (660, 677, "T4_DYNAMIC_GRID_RECONFIG", "central_dominant", 73),
        (682, 683, "T4_MICRO_GLITCH", "slices_rgb", 74),
        (694, 701, "T4_RECTANGULAR_BLOCK_STUTTER", "horizontal_media_blocks", 75),
        (704, 717, "T4_TILE_REVEAL", "staggered_mosaic", 76),
        (722, 725, "T4_SHAKE_IMPACT", "damped_impact", 77),
        (736, 753, "T4_DYNAMIC_GRID_RECONFIG", "offset_2x2", 78),
        (758, 759, "T4_MICRO_GLITCH", "rgb_offset", 79),
        (770, 783, "T4_TILE_REVEAL", "checker_reveal", 80),
        (788, 791, "T4_SHAKE_IMPACT", "damped_impact", 81),
        (800, 809, "T4_TILE_REVEAL", "settle_to_stable_tail", 82),
    ],
}


def build() -> dict:
    events = []
    ordinal = 1
    for scene_id in ("S1", "S2", "S3", "S4"):
        for start, end, family, variant, seed in SCHEDULE[scene_id]:
            events.append({
                "event_id": f"T4-E{ordinal:02d}",
                "scene_id": scene_id,
                "family": family,
                "variant": variant,
                "seed": seed,
                "frames": [start, end],
                "start_seconds_exact": round(start / FPS, 6),
                "end_seconds_exclusive_exact": round((end + 1) / FPS, 6),
                "duration_frames": end - start + 1,
            })
            ordinal += 1
    events.sort(key=lambda item: item["frames"][0])
    for left, right in zip(events, events[1:]):
        if left["frames"][1] >= right["frames"][0]:
            raise ValueError(f"Overlapping events: {left['event_id']} and {right['event_id']}")
    covered_frames = sum(item["duration_frames"] for item in events)
    family_frames = Counter()
    family_events = Counter()
    for event in events:
        family_frames[event["family"]] += event["duration_frames"]
        family_events[event["family"]] += 1
    stable_frames = TOTAL - covered_frames
    return {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "title": "Fusion transitionnelle A+B+C+D sur 30 secondes",
        "status": "implemented_candidate_pending_owner_review_of_silent_render",
        "approval_state": {
            "reference_fusion_owner_approved": True,
            "reference_fusion_approval": "approvals/APPROBATION_TRANSITIONS_T4_V3_2026-11-19.json",
            "questions_capture_and_12_screens_implemented": True,
            "numeric_timeline": "engine_decision_pending_silent_render_review",
            "silent_render": "not_created_at_contract_build_time"
        },
        "truth_model": {
            "OBSERVED": "Famille de mouvement visible dans une preview CapCut inspectée à dix images par seconde.",
            "OWNER_APPROVED": "Rôle A+B+C+D explicitement validé par le propriétaire.",
            "ENGINE_DECISION": "Fenêtre, amplitude et cadence déterministes choisies pour le moteur T4; elles ne prétendent pas mesurer exactement CapCut.",
            "rule": "La grammaire est adaptée avec des médias T4 distincts; aucun contenu, texte, son, watermark ou univers des previews n'est repris."
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
            "scene_durations_seconds": [6, 8, 7, 9],
            "scene_frame_ranges_inclusive": {
                "S1": [0, 179],
                "S2": [180, 419],
                "S3": [420, 629],
                "S4": [630, 899]
            }
        },
        "source_references": [
            {
                "slot": "A",
                "title": "PuzzleGlitch",
                "url": "https://www.capcut.com/template-detail/PuzzleGlitch/7573632958570106117",
                "preview_sha256": "a63b1f05a11c3e5abb288599941bbdf4f91c811081a2bfe0cb6e9942cad62dad",
                "approved_role": "structural_core_tile_reveal"
            },
            {
                "slot": "B",
                "title": "Grid Style",
                "url": "https://www.capcut.com/template-detail/Grid-Style/7270677670365629702",
                "preview_sha256": "e6f78ba1d53396aa39794b4203670bdfdbdc33c4529e7389be2848eaec73a21d",
                "approved_role": "multi_plan_grid_reconfiguration"
            },
            {
                "slot": "C",
                "title": "Shake Transition",
                "url": "https://www.capcut.com/template-detail/fyp-foryou-caredit-capcuttopcreator-popo-hrtz/7601360400000568577",
                "preview_sha256": "0cecb596c09cac559ca907c9bf7fe386eb5460555b23839fa13ce86422a52af0",
                "approved_role": "impact_shake_and_rectangular_breaks"
            },
            {
                "slot": "D",
                "title": "Glitch effect shake",
                "url": "https://www.capcut.com/template-detail/Glitch-effect-shake/7346375274763914501",
                "preview_sha256": "e2392212174cf233adc7f917e8669a2279b7d8b23734c1e7462748ee7254f7a9",
                "approved_role": "one_to_three_frame_micro_glitches"
            }
        ],
        "owner_constraints": {
            "copy_reference_content_forbidden": True,
            "visible_blocks_inside_scenes_required": True,
            "constant_reconfiguration_in_active_passages_required": True,
            "impact_vibration_required": True,
            "return_to_stable_full_frame_required": True,
            "blue_or_cyan_separator_lines_forbidden": True,
            "solid_color_transition_bars_forbidden": True,
            "silent_render_text_forbidden": True,
            "silent_render_audio_forbidden": True,
            "s4_final_stable_tail_frames": 90
        },
        "transition_parameter_profiles": {
            "T4_TILE_REVEAL": {
                "truth": "ENGINE_DECISION",
                "grid_candidates": ["4x6", "5x8"],
                "visible_tile_count_range": [5, 16],
                "alternate_time_offsets_frames": [12, 24, 39, 57],
                "frame_coverage_peak_range": [0.42, 0.72],
                "gap_px": 0,
                "edge_softness_px_max": 1.5,
                "exact_frame_duplicate_forbidden": True
            },
            "T4_DYNAMIC_GRID_RECONFIG": {
                "truth": "ENGINE_DECISION",
                "panel_count_range": [3, 7],
                "layouts": ["central_dominant", "three_columns", "offset_2x2", "face_safe_satellites"],
                "panel_gap_px_range": [0, 4],
                "panel_gap_color": "source_derived_near_black",
                "dominant_panel_min_area_ratio": 0.34,
                "separator_lines": False,
                "separator_color": None
            },
            "T4_SHAKE_IMPACT": {
                "truth": "ENGINE_DECISION",
                "translation_x_px_at_720_range": [7, 14],
                "translation_y_px_at_720_range": [4, 10],
                "rotation_deg_range": [-0.65, 0.65],
                "scale_pulse_range": [1.015, 1.04],
                "overscan_scale": 1.05,
                "decay": "alternating_damped",
                "face_safe_amplitude_multiplier": 0.62,
                "continuous_shake_forbidden": True
            },
            "T4_RECTANGULAR_BLOCK_STUTTER": {
                "truth": "ENGINE_DECISION",
                "block_count_range": [2, 7],
                "block_height_ratio_range": [0.025, 0.12],
                "content": "alternate_temporal_window_only",
                "solid_color_bars_forbidden": True
            },
            "T4_MICRO_GLITCH": {
                "truth": "ENGINE_DECISION",
                "duration_frames_range": [1, 3],
                "horizontal_slice_count_range": [3, 8],
                "slice_offset_px_at_720_range": [-18, 18],
                "rgb_offset_px_at_720_range": [2, 7],
                "affected_frame_area_max_ratio": 0.28,
                "face_safe_center_box_normalized": [0.2, 0.12, 0.8, 0.72],
                "persistent_vhs_noise_forbidden": True,
                "full_frame_white_flash_forbidden": True
            }
        },
        "protected_stable_windows": [
            {
                "scene_id": "S3",
                "frames": [467, 548],
                "reason": "Préserver la bouchée et le début de la réaction réelle."
            },
            {
                "scene_id": "S4",
                "frames": [810, 899],
                "reason": "Atterrissage plein écran stable de trois secondes."
            }
        ],
        "cadence_audit": {
            "total_events": len(events),
            "covered_effect_frames": covered_frames,
            "default_stable_frames": stable_frames,
            "default_stable_share": round(stable_frames / TOTAL, 6),
            "tile_plus_grid_share": round((family_frames["T4_TILE_REVEAL"] + family_frames["T4_DYNAMIC_GRID_RECONFIG"]) / TOTAL, 6),
            "shake_micro_and_block_share": round((family_frames["T4_SHAKE_IMPACT"] + family_frames["T4_MICRO_GLITCH"] + family_frames["T4_RECTANGULAR_BLOCK_STUTTER"]) / TOTAL, 6),
            "family_event_counts": dict(sorted(family_events.items())),
            "family_frame_counts": dict(sorted(family_frames.items())),
            "active_break_interval_seconds_target": [0.35, 0.70],
            "stable_windows_are_intentional_exceptions": True
        },
        "timeline_events": events
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "reverse-engineering/T4_TRANSITIONS_30S.json")
    args = parser.parse_args()
    contract = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"T4_TRANSITION_CONTRACT_BUILT {len(contract['timeline_events'])} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
