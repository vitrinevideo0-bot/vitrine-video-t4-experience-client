#!/usr/bin/env python3
"""Build the executable 12-screen T4 capture flow from the approved simple-French JSON sources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def screen_label(ordinal: int, state: str) -> str:
    labels = {
        "A_GUIDE": "A / GUIDE",
        "B_RECORDING": "B / ENREGISTREMENT",
        "C_REVIEW": "C / VÉRIFICATION",
    }
    return f"ÉCRAN {ordinal:02d} — {labels[state]}"


def build(guide: dict[str, Any], questions: dict[str, Any], guide_path: Path, questions_path: Path) -> dict[str, Any]:
    scenes = guide["scenes"]
    if len(scenes) != 4:
        raise ValueError("T4 requires exactly four scenes")
    if [int(scene["secondes"]) for scene in scenes] != [6, 8, 7, 9]:
        raise ValueError("T4 scene durations must be 6/8/7/9 seconds")
    field_ids = [field["id"] for field in questions["fields"]]
    if field_ids != ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"]:
        raise ValueError("T4 merchant fields must remain compatible with T1/T2/T3")
    for expected, scene in enumerate(scenes, 1):
        if scene["n"] != expected or scene["total"] != 4:
            raise ValueError("T4 scene numbering must remain 1/4 through 4/4")
        prompts = scene["recording_prompts"]
        if len(prompts) != 1 or prompts[0] != {
            "from_ms": 0,
            "to_ms": int(scene["secondes"]) * 1000,
            "text": scene["recording_prompt"],
        }:
            raise ValueError("Each T4 recording screen must expose the one owner-approved instruction")

    screens: list[dict[str, Any]] = []
    for scene_index, scene in enumerate(scenes, 1):
        scene_id = f"S{scene_index}"
        seconds = int(scene["secondes"])
        duration_ms = seconds * 1000
        prefix = f"T4_CAPTURE_{scene_id}"
        next_scene = f"T4_CAPTURE_S{scene_index + 1}_A_GUIDE" if scene_index < 4 else "T4_RENDER_CONFIRMATION"
        guide_ordinal = len(screens) + 1
        recording_ordinal = len(screens) + 2
        review_ordinal = len(screens) + 3
        scene_counter = f"SCÈNE {scene_index} SUR 4 — {seconds} SECONDES"
        base = {
            "scene_id": scene_id,
            "scene_index": scene_index,
            "scene_total": 4,
            "capture_duration_ms": duration_ms,
            "capture_slot": f"captures.{scene_id}",
        }

        guide_screen = {
            **base,
            "ordinal": guide_ordinal,
            "screen_id": f"{prefix}_A_GUIDE",
            "route_key": f"t4.capture.s{scene_index}.guide",
            "state": "A_GUIDE",
            "display_state": "A / GUIDE",
            "purpose": scene["fonction_commerciale"],
            "bindings": {
                "title": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/titre",
                "instruction": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/consigne",
                "film_list": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/a_filmer",
                "avoid_list": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/a_eviter",
                "required_action": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/ce_que_tu_dois_faire",
                "after_action_note": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/note_apres_action",
                "speech_note": "capture-guide/consignes_T4.json#/mention_langues_commune",
                "silence_note": "capture-guide/consignes_T4.json#/mention_silence_facultatif",
                "primary_action": "capture-guide/consignes_T4.json#/bouton_principal",
            },
            "resolved_text": {
                "screen_label": screen_label(guide_ordinal, "A_GUIDE"),
                "scene_counter": scene_counter,
                "duration": f"{seconds} secondes",
                "title": scene["titre"],
                "guide_section_title": guide["guide_section_title"],
                "instruction": scene["consigne"],
                "film_section_title": guide["film_section_title"],
                "film_list": scene["a_filmer"],
                "avoid_section_title": guide["avoid_section_title"],
                "avoid_list": scene["a_eviter"],
                "action_section_title": guide["action_section_title"],
                "required_action": scene["ce_que_tu_dois_faire"],
                "after_action_note": scene["note_apres_action"],
                "speech_section_title": guide["speech_section_title"],
                "voice_note": guide["mention_langues_commune"],
                "silence_note": guide["mention_silence_facultatif"],
                "primary_action": guide["bouton_principal"],
            },
            "visible_components": [
                "screen_label",
                "scene_counter",
                "title",
                "what_to_film",
                "film_list",
                "avoid_list",
                "required_action",
                "consent_note_when_applicable",
                "speech_note",
                "start_recording_button",
            ],
            "forbidden_components": [
                "recording_timer",
                "review_actions",
                "automatic_subtitles",
                "abstract_instruction_text",
            ],
            "actions": [
                {
                    "event": "START_RECORDING",
                    "label": guide["bouton_principal"],
                    "effects": [
                        "request_camera_permission",
                        "request_microphone_permission",
                        "run_COUNTDOWN_3_2_1",
                    ],
                    "next_screen_id": f"{prefix}_B_RECORDING",
                }
            ],
            "proof_png": f"ui-screens/{prefix}_A_GUIDE.png",
        }

        recording_screen = {
            **base,
            "ordinal": recording_ordinal,
            "screen_id": f"{prefix}_B_RECORDING",
            "route_key": f"t4.capture.s{scene_index}.recording",
            "state": "B_RECORDING",
            "display_state": "B / ENREGISTREMENT",
            "purpose": f"Filmer automatiquement pendant {seconds} secondes avec le son.",
            "bindings": {
                "elapsed_ms": "runtime.capture.elapsed_ms",
                "progress_0_to_1": "runtime.capture.progress",
                "prompt": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/recording_prompt",
                "prompt_timeline": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/recording_prompts",
                "output_uri": f"runtime.captures.{scene_id}.uri",
            },
            "resolved_text": {
                "screen_label": screen_label(recording_ordinal, "B_RECORDING"),
                "scene_counter": scene_counter,
                "recording_status": guide["recording_status"],
                "instruction": scene["recording_prompt"],
                "timer_initial": f"Temps restant : 00:00 / 00:{seconds:02d}",
                "timer_prefix": "Temps restant :",
                "timer_total": f"00:{seconds:02d}",
                "audio_status": guide["recording_audio_status"],
                "orientation_status": guide["recording_orientation_status"],
                "auto_stop_status": f"Arrêt automatique à la fin des {seconds} secondes.",
                "duration_seconds": seconds,
                "prompt_timeline": scene["recording_prompts"],
            },
            "visible_components": [
                "screen_label",
                "scene_counter",
                "recording_status",
                "current_recording_instruction",
                "recording_timer",
                "microphone_active",
                "vertical_video_status",
                "automatic_stop_status",
            ],
            "forbidden_components": [
                "instruction_sheet",
                "merchant_fields",
                "manual_stop_button",
                "review_actions",
                "automatic_subtitles",
                "extra_recording_prompt",
            ],
            "capture": {
                "starts_after": "COUNTDOWN_3_2_1_COMPLETE",
                "video": True,
                "microphone_audio": True,
                "orientation": "vertical",
                "source_speed": 1.0,
                "source_time_map": "identity",
                "audio_time_map": "identity",
                "duration_ms": duration_ms,
                "auto_stop": True,
                "manual_stop": False,
                "write_to": f"runtime.captures.{scene_id}.uri",
            },
            "actions": [
                {
                    "event": "CAPTURE_DURATION_REACHED",
                    "effects": [
                        "stop_recorder",
                        "finalize_capture_file",
                        "probe_capture_metadata",
                        "open_audio_review",
                    ],
                    "next_screen_id": f"{prefix}_C_REVIEW",
                }
            ],
            "proof_png": f"ui-screens/{prefix}_B_RECORDING.png",
        }

        review_screen = {
            **base,
            "ordinal": review_ordinal,
            "screen_id": f"{prefix}_C_REVIEW",
            "route_key": f"t4.capture.s{scene_index}.review",
            "state": "C_REVIEW",
            "display_state": "C / VÉRIFICATION",
            "purpose": "Regarder la vidéo avec le son, puis la garder ou la refaire.",
            "bindings": {
                "preview_uri": f"runtime.captures.{scene_id}.uri",
                "capture_metadata": f"runtime.captures.{scene_id}.metadata",
                "review_question": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/review_question",
                "review_checks": f"capture-guide/consignes_T4.json#/scenes/{scene_index - 1}/review_checks",
            },
            "resolved_text": {
                "screen_label": screen_label(review_ordinal, "C_REVIEW"),
                "take_label": f"PRISE {scene_index} — 0:{seconds:02d}",
                "audio_status": guide["review_audio_status"],
                "review_question": scene["review_question"],
                "review_checks": scene["review_checks"],
                "redo_action": guide["redo_action"],
                "positive_action": scene["positive_action"],
            },
            "visible_components": [
                "screen_label",
                "captured_video_preview",
                "captured_audio_playback",
                "review_question",
                "review_checklist",
                "redo_button",
                "accept_button",
            ],
            "forbidden_components": [
                "instruction_sheet",
                "recording_timer",
                "recording_progress",
                "automatic_subtitles",
                "extra_error_copy",
            ],
            "playback": {
                "audio": True,
                "loop": True,
                "source_speed": 1.0,
            },
            "actions": [
                {
                    "event": "RETAKE",
                    "label": guide["redo_action"],
                    "effects": [
                        f"delete:runtime.captures.{scene_id}",
                        "reset_scene_capture_state",
                    ],
                    "next_screen_id": f"{prefix}_A_GUIDE",
                },
                {
                    "event": "ACCEPT_CAPTURE",
                    "label": scene["positive_action"],
                    "effects": [
                        f"persist:runtime.captures.{scene_id}",
                        "mark_capture_accepted",
                    ],
                    "next_screen_id": next_scene,
                },
            ],
            "proof_png": f"ui-screens/{prefix}_C_REVIEW.png",
        }
        screens.extend([guide_screen, recording_screen, review_screen])

    return {
        "schema_version": "1.0.0",
        "contract_id": "restauration_t4_experience_client_capture_flow_v1_0_0",
        "template_id": "RESTAURATION-T4",
        "template_version": "1.0.0",
        "status": "owner_approved_simple_french_executable_contract",
        "copy_revision": guide["copy_revision"],
        "sources": {
            "guide": {
                "path": "capture-guide/consignes_T4.json",
                "sha256": sha256(guide_path),
            },
            "questions": {
                "path": "form/questions_T4.json",
                "sha256": sha256(questions_path),
            },
        },
        "counts": {
            "merchant_questions": 6,
            "scenes": 4,
            "states_per_scene": 3,
            "stable_capture_screens": 12,
        },
        "scene_durations_ms": [6000, 8000, 7000, 9000],
        "transient_states": [
            {
                "id": "COUNTDOWN_3_2_1",
                "counted_in_12_stable_screens": False,
                "sequence": [3, 2, 1],
                "trigger": "START_RECORDING",
                "then": "B_RECORDING",
                "must_not_be_written_into_capture": True,
            }
        ],
        "runtime_rules": {
            "camera_required": True,
            "microphone_requested": True,
            "speech_optional": True,
            "playback_audio_enabled": True,
            "silent_render_audio_enabled": False,
            "source_speed": 1.0,
            "video_orientation": "vertical",
            "automatic_subtitles": False,
            "retake_deletes_previous_capture": True,
            "simple_french_copy_required": True,
        },
        "screens": screens,
        "session_model": {
            "name": "T4ExperienceClientSession",
            "fields": [
                "merchant_payload",
                "captures",
                "current_screen_id",
                "accepted_scene_ids",
            ],
            "persistence": "persist accepted content URIs and probed media metadata until RenderJob submission",
        },
        "renderer_handoff": {
            "trigger": "ACCEPT_CAPTURE on T4_CAPTURE_S4_C_REVIEW",
            "render_job": "demo/render_job_silent_demo.json",
            "template_contract": "config/T4_EXPERIENCE_CLIENT_TEMPLATE_V1_0_0.json",
            "capture_bindings": {
                "captures.S1": "runtime.captures.S1.uri",
                "captures.S2": "runtime.captures.S2.uri",
                "captures.S3": "runtime.captures.S3.uri",
                "captures.S4": "runtime.captures.S4.uri",
            },
            "merchant_payload_source": "form/questions_T4.json",
            "merchant_payload_targets": [
                "merchant_payload.nom",
                "merchant_payload.produit",
                "merchant_payload.prix",
                "merchant_payload.whatsapp",
                "merchant_payload.quartier",
                "merchant_payload.accroche",
            ],
            "production_render_plane": "github_actions",
            "cloudflare_rendering_forbidden": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guide", type=Path, default=ROOT / "capture-guide/consignes_T4.json")
    parser.add_argument("--questions", type=Path, default=ROOT / "form/questions_T4.json")
    parser.add_argument("--output", type=Path, default=ROOT / "config/T4_CAPTURE_FLOW_V1_0_0.json")
    args = parser.parse_args()
    guide = json.loads(args.guide.read_text(encoding="utf-8"))
    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    contract = build(guide, questions, args.guide, args.questions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"T4_CAPTURE_FLOW_BUILT {len(contract['screens'])} {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
