from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class T4ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.questions = load("form/questions_T4.json")
        cls.guide = load("capture-guide/consignes_T4.json")
        cls.flow = load("config/T4_CAPTURE_FLOW_V1_0_0.json")
        cls.template = load("config/T4_EXPERIENCE_CLIENT_TEMPLATE_V3_0_0.json")
        cls.creative = load("config/T4_HYBRID_CINEMATIC_TRANSITIONS_V3_0_0.json")
        cls.choice = load("approvals/CHOIX_TRANSITIONS_HYBRIDES_V3_2026-11-18.json")
        cls.transitions = load("reverse-engineering/T4_TRANSITIONS_HYBRIDES_30S_V3.json")
        cls.rushes = load("rushes/manifest.json")
        cls.ui = load("ui-screens/manifest.json")
        cls.job = load("demo/render_job_hybrid_v3.json")

    def test_exact_format_and_scene_durations(self) -> None:
        fmt = self.template["format"]
        self.assertEqual((fmt["width"], fmt["height"], fmt["fps"], fmt["frames"]), (720, 1280, 30, 900))
        self.assertEqual(fmt["scene_durations_s"], [6, 8, 7, 9])
        self.assertEqual(sum(fmt["scene_durations_s"]), 30)
        self.assertEqual([scene["secondes"] for scene in self.guide["scenes"]], [6, 8, 7, 9])
        self.assertEqual([scene["duration_seconds"] for scene in self.rushes["scenes"]], [6, 8, 7, 9])

    def test_six_canonical_questions(self) -> None:
        fields = self.questions["fields"]
        self.assertEqual([field["id"] for field in fields], ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"])
        self.assertEqual([field["id"] for field in fields if field["required"]], ["nom", "produit", "prix", "whatsapp", "quartier"])
        self.assertFalse(fields[-1]["required"])
        self.assertEqual([field["json_target"] for field in fields], [f"merchant_payload.{name}" for name in ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"]])
        self.assertTrue(self.questions["compatibility_with_t1_t2_t3"]["invented_content_forbidden"])

    def test_exact_four_scene_names(self) -> None:
        self.assertEqual([scene["titre"] for scene in self.guide["scenes"]], ["BIENVENUE", "LE SERVICE", "LA DÉGUSTATION", "VENEZ / COMMANDEZ"])
        self.assertTrue(all(len(scene["recording_prompts"]) == 3 for scene in self.guide["scenes"]))
        self.assertTrue(all(len(scene["review_checks"]) == 3 for scene in self.guide["scenes"]))
        self.assertIn("consent", json.dumps(self.guide["scenes"][2], ensure_ascii=False).lower())

    def test_exact_twelve_screen_flow(self) -> None:
        screens = self.flow["screens"]
        self.assertEqual(len(screens), 12)
        expected = []
        for scene in range(1, 5):
            expected.extend([
                (scene, "A_GUIDE", f"T4_CAPTURE_S{scene}_A_GUIDE"),
                (scene, "B_RECORDING", f"T4_CAPTURE_S{scene}_B_RECORDING"),
                (scene, "C_REVIEW", f"T4_CAPTURE_S{scene}_C_REVIEW"),
            ])
        self.assertEqual([(item["scene_index"], item["state"], item["screen_id"]) for item in screens], expected)
        self.assertEqual([item["ordinal"] for item in screens], list(range(1, 13)))
        self.assertEqual(self.flow["counts"], {"merchant_questions": 6, "scenes": 4, "states_per_scene": 3, "stable_capture_screens": 12})

    def test_recording_and_review_runtime_rules(self) -> None:
        recordings = [item for item in self.flow["screens"] if item["state"] == "B_RECORDING"]
        reviews = [item for item in self.flow["screens"] if item["state"] == "C_REVIEW"]
        self.assertEqual([item["capture"]["duration_ms"] for item in recordings], [6000, 8000, 7000, 9000])
        self.assertTrue(all(item["capture"]["auto_stop"] for item in recordings))
        self.assertTrue(all(not item["capture"]["manual_stop"] for item in recordings))
        self.assertTrue(all(item["capture"]["source_speed"] == 1.0 for item in recordings))
        self.assertTrue(all(item["playback"]["audio"] for item in reviews))
        self.assertTrue(self.flow["runtime_rules"]["silent_render_audio_enabled"] is False)
        self.assertEqual(reviews[-1]["actions"][1]["next_screen_id"], "T4_RENDER_CONFIRMATION")

    def test_ui_manifest_and_png_proofs(self) -> None:
        self.assertEqual(self.ui["stable_screen_count"], 12)
        self.assertEqual(len(self.ui["screens"]), 12)
        self.assertFalse(self.ui["external_media_used"])
        for record in self.ui["screens"]:
            path = ROOT / "ui-screens" / record["file"]
            self.assertTrue(path.exists(), path)
            self.assertEqual(sha256(path), record["sha256"])
            with Image.open(path) as image:
                self.assertEqual(image.size, (720, 1280))
        board = ROOT / "ui-screens" / self.ui["board"]
        self.assertEqual(sha256(board), self.ui["board_sha256"])

    def test_owner_explicitly_selected_hybrid_cinematic(self) -> None:
        self.assertEqual(self.choice["reviewed_candidate"]["verdict"], "rejected_as_too_basic")
        self.assertEqual(self.choice["selected_option"]["id"], "hybride_cinematique")
        self.assertEqual(self.choice["selected_option"]["selection_method"], "explicit_owner_choice")
        decisions = self.choice["active_decisions"]
        self.assertEqual(decisions["transition_count"], 3)
        self.assertEqual(decisions["transition_cut_seconds"], [6, 14, 21])
        self.assertEqual(decisions["transition_duration_frames_each"], 8)
        self.assertTrue(decisions["full_frame_only"])
        self.assertTrue(decisions["effects_inside_stable_rush_windows_forbidden"])
        self.assertEqual([item["family"] for item in self.choice["transition_signatures"]], [
            "T4_CINEMATIC_WHIP_PAN",
            "T4_CINEMATIC_ZOOM_MATCH",
            "T4_CINEMATIC_WHIP_ZOOM",
        ])

    def test_candidate_history_records_both_rejections(self) -> None:
        self.assertEqual([(item["version"], item["status"], item["reason"]) for item in self.creative["candidate_history"]], [
            ("1.0.0", "rejected", "too_exaggerated_inside_rushes"),
            ("2.0.0", "rejected", "too_basic_at_rush_changes"),
        ])
        self.assertEqual([item["creative_verdict"] for item in self.template["candidate_history"]], ["too_exaggerated", "too_basic"])

    def test_exact_three_hybrid_transition_windows(self) -> None:
        events = self.transitions["timeline_events"]
        self.assertEqual(len(events), 3)
        self.assertEqual([event["cut_frame"] for event in events], [180, 420, 630])
        self.assertEqual([event["frames"] for event in events], [[176, 183], [416, 423], [626, 633]])
        self.assertEqual([event["family"] for event in events], [
            "T4_CINEMATIC_WHIP_PAN",
            "T4_CINEMATIC_ZOOM_MATCH",
            "T4_CINEMATIC_WHIP_ZOOM",
        ])
        self.assertEqual([event["variant"] for event in events], [
            "fast_horizontal_whip_to_service",
            "plate_to_tasting_zoom_through",
            "portrait_to_ambience_opening",
        ])
        self.assertTrue(all(event["duration_frames"] == 8 for event in events))
        self.assertTrue(all(event["full_frame_only"] for event in events))
        self.assertTrue(all(event["clean_endpoint_frames_required"] for event in events))

    def test_impressive_parameters_are_bounded(self) -> None:
        profiles = self.transitions["transition_parameter_profiles"]
        whip = profiles["T4_CINEMATIC_WHIP_PAN"]
        zoom = profiles["T4_CINEMATIC_ZOOM_MATCH"]
        opening = profiles["T4_CINEMATIC_WHIP_ZOOM"]
        self.assertEqual(whip["maximum_horizontal_translation_px"], 110)
        self.assertEqual(whip["maximum_horizontal_blur_kernel_px"], 41)
        self.assertLessEqual(whip["maximum_scale"], 1.04)
        self.assertEqual(zoom["maximum_outgoing_scale"], 1.34)
        self.assertEqual(zoom["maximum_incoming_entry_scale"], 1.22)
        self.assertFalse(zoom["flash"])
        self.assertEqual(opening["maximum_horizontal_blur_kernel_px"], 31)
        self.assertEqual(opening["incoming_landing_scale"], 1.0)
        self.assertTrue(all(profile["endpoint_frames_clean"] for profile in profiles.values()))
        self.assertTrue(all(profile["full_frame_only"] for profile in profiles.values()))

    def test_no_transition_outside_cut_windows_and_97_percent_stable(self) -> None:
        audit = self.transitions["cadence_audit"]
        self.assertEqual(audit["total_events"], 3)
        self.assertEqual(audit["events_outside_rush_change_windows"], 0)
        self.assertEqual(audit["covered_transition_frames"], 24)
        self.assertEqual(audit["stable_full_frame_frames"], 876)
        self.assertGreaterEqual(audit["stable_full_frame_share"], 0.97)
        self.assertEqual(audit["distinct_transition_family_count"], 3)
        self.assertFalse(any(event["frames"][0] <= 899 and event["frames"][1] >= 810 for event in self.transitions["timeline_events"]))

    def test_decorative_v1_effects_remain_forbidden(self) -> None:
        owner = self.transitions["owner_constraints"]
        self.assertTrue(owner["transitions_only_around_rush_changes_required"])
        self.assertTrue(owner["three_distinct_cinematic_signatures_required"])
        self.assertTrue(owner["clean_landing_on_incoming_rush_required"])
        for key in [
            "mosaic_forbidden",
            "dynamic_grid_forbidden",
            "multi_panel_forbidden",
            "glitch_forbidden",
            "rgb_split_forbidden",
            "rectangular_block_stutter_forbidden",
            "solid_color_transition_bars_forbidden",
            "blue_or_cyan_separator_lines_forbidden",
        ]:
            self.assertTrue(owner[key], key)

    def test_no_audio_or_burned_text(self) -> None:
        owner = self.transitions["owner_constraints"]
        self.assertTrue(owner["silent_render_text_forbidden"])
        self.assertTrue(owner["silent_render_audio_forbidden"])
        self.assertFalse(self.template["format"]["silent_candidate_burned_text"])
        self.assertEqual(self.template["format"]["silent_candidate_audio_streams"], 0)
        profile = self.job["render_profile"]
        self.assertFalse(profile["burn_merchant_text"])
        self.assertFalse(profile["include_capture_audio"])
        self.assertFalse(profile["include_music"])
        self.assertFalse(profile["include_voice_over"])
        self.assertFalse(self.job["output"]["audio"])
        self.assertFalse(self.job["output"]["burned_text"])

    def test_four_licensed_hash_locked_rushes(self) -> None:
        self.assertEqual(len(self.rushes["scenes"]), 4)
        self.assertFalse(self.rushes["license"]["raw_media_committed"])
        self.assertFalse(self.rushes["license"]["raw_media_published_as_artifact"])
        self.assertEqual(len({scene["pexels_id"] for scene in self.rushes["scenes"]}), 4)
        self.assertTrue(all(len(scene["sha256"]) == 64 for scene in self.rushes["scenes"]))
        self.assertTrue(all(scene["source_duration_seconds"] - scene["trim_start_seconds"] >= scene["duration_seconds"] for scene in self.rushes["scenes"]))

    def test_render_job_is_v3_hybrid_and_silent(self) -> None:
        self.assertEqual(self.job["template_version"], "3.0.0")
        self.assertEqual(list(self.job["merchant_payload"]), ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"])
        self.assertEqual(self.job["render_profile"]["transition_style"], "three_distinct_impressive_full_frame_transitions_at_rush_changes_only")
        self.assertEqual(self.job["render_profile"]["transition_signatures"], ["whip_pan", "zoom_match_through_plate", "whip_zoom_opening"])
        self.assertEqual(self.job["output"]["filename"], "VIDEO_T4_EXPERIENCE_CLIENT_TRANSITIONS_HYBRIDES_V3_A_VALIDER.mp4")

    def test_all_active_linked_contract_files_exist(self) -> None:
        paths = [
            self.template["merchant_payload"]["source"],
            self.template["capture"]["guide"],
            self.template["capture"]["flow_contract"],
            self.template["capture"]["visual_proof_manifest"],
            self.template["capture"]["visual_proof_board"],
            self.template["creative_contracts"]["implementation_authorization"],
            self.template["creative_contracts"]["owner_hybrid_choice"],
            self.template["creative_contracts"]["active_creative_contract"],
            self.template["creative_contracts"]["active_transition_timeline"],
            self.template["demo_media"]["manifest"],
            self.template["runtime_contracts"]["render_job"],
            self.template["runtime_contracts"]["renderer"],
            self.template["runtime_contracts"]["validator"],
        ]
        self.assertTrue(all((ROOT / path).exists() for path in paths), paths)
        self.assertEqual(self.template["runtime_contracts"]["production_render_plane"], "github_actions")
        self.assertTrue(self.template["runtime_contracts"]["cloudflare_rendering_forbidden"])
        self.assertTrue(self.template["guardrails"]["transitions_only_around_rush_changes"])
        self.assertTrue(self.template["guardrails"]["three_distinct_cinematic_signatures"])


if __name__ == "__main__":
    unittest.main()
