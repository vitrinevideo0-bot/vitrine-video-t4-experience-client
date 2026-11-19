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
        cls.template = load("config/T4_EXPERIENCE_CLIENT_TEMPLATE_V2_0_0.json")
        cls.creative = load("config/T4_NATURAL_TRANSITIONS_CONTRACT_V2_0_0.json")
        cls.feedback = load("approvals/CORRECTION_TRANSITIONS_NATURELLES_V2_2026-11-18.json")
        cls.transitions = load("reverse-engineering/T4_TRANSITIONS_NATURELLES_30S_V2.json")
        cls.rushes = load("rushes/manifest.json")
        cls.ui = load("ui-screens/manifest.json")
        cls.job = load("demo/render_job_natural_v2.json")

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

    def test_owner_correction_supersedes_exaggerated_v1_style(self) -> None:
        self.assertEqual(self.feedback["reviewed_candidate"]["verdict"], "rejected_for_transition_exaggeration")
        decisions = self.feedback["active_decisions"]
        self.assertEqual(decisions["transition_count"], 3)
        self.assertEqual(decisions["transition_cut_seconds"], [6, 14, 21])
        self.assertEqual(decisions["maximum_transition_frames_at_30_fps"], 4)
        self.assertTrue(decisions["full_frame_between_cuts"])
        self.assertTrue(all(decisions[key] for key in [
            "mosaic_forbidden",
            "dynamic_grid_forbidden",
            "shake_forbidden",
            "glitch_forbidden",
            "rectangular_block_stutter_forbidden",
        ]))
        self.assertEqual(self.creative["previous_candidate"]["status"], "rejected")

    def test_exact_three_natural_transition_windows(self) -> None:
        events = self.transitions["timeline_events"]
        self.assertEqual(len(events), 3)
        self.assertEqual([event["cut_frame"] for event in events], [180, 420, 630])
        self.assertEqual([event["frames"] for event in events], [[180, 183], [420, 423], [630, 633]])
        self.assertTrue(all(event["family"] == "T4_NATURAL_SPEED_CUT" for event in events))
        self.assertTrue(all(event["variant"] == "fast_soft_motion_dissolve" for event in events))
        self.assertTrue(all(event["duration_frames"] == 4 for event in events))
        self.assertTrue(all(event["full_frame_only"] for event in events))
        for left, right in zip(events, events[1:]):
            self.assertLess(left["frames"][1], right["frames"][0])

    def test_no_transition_inside_a_rush_and_98_percent_stable(self) -> None:
        audit = self.transitions["cadence_audit"]
        self.assertEqual(audit["total_events"], 3)
        self.assertEqual(audit["events_outside_rush_changes"], 0)
        self.assertEqual(audit["covered_transition_frames"], 12)
        self.assertEqual(audit["stable_full_frame_frames"], 888)
        self.assertGreaterEqual(audit["stable_full_frame_share"], 0.98)
        self.assertEqual(audit["maximum_event_duration_frames"], 4)
        self.assertFalse(any(event["frames"][0] <= 899 and event["frames"][1] >= 810 for event in self.transitions["timeline_events"]))

    def test_all_exaggerated_effect_families_are_forbidden(self) -> None:
        owner = self.transitions["owner_constraints"]
        self.assertTrue(owner["transitions_only_at_rush_changes_required"])
        self.assertTrue(owner["full_frame_between_cuts_required"])
        for key in [
            "mosaic_forbidden",
            "dynamic_grid_forbidden",
            "shake_forbidden",
            "glitch_forbidden",
            "rectangular_block_stutter_forbidden",
            "solid_color_transition_bars_forbidden",
            "blue_or_cyan_separator_lines_forbidden",
        ]:
            self.assertTrue(owner[key], key)
        profile = self.transitions["transition_parameter_profiles"]["T4_NATURAL_SPEED_CUT"]
        self.assertEqual(profile["maximum_motion_blur_kernel_px"], 5)
        self.assertEqual(profile["translation_px"], 0)
        self.assertEqual(profile["rotation_degrees"], 0)
        self.assertEqual(profile["scale"], 1.0)
        self.assertEqual(profile["panels"], 1)
        self.assertTrue(profile["full_frame_only"])

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

    def test_render_job_is_v2_natural_and_silent(self) -> None:
        self.assertEqual(self.job["template_version"], "2.0.0")
        self.assertEqual(list(self.job["merchant_payload"]), ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"])
        self.assertEqual(self.job["render_profile"]["transition_style"], "three_fast_soft_motion_dissolves_at_rush_changes_only")
        self.assertEqual(self.job["output"]["filename"], "VIDEO_T4_EXPERIENCE_CLIENT_TRANSITIONS_NATURELLES_V2_A_VALIDER.mp4")

    def test_all_active_linked_contract_files_exist(self) -> None:
        paths = [
            self.template["merchant_payload"]["source"],
            self.template["capture"]["guide"],
            self.template["capture"]["flow_contract"],
            self.template["capture"]["visual_proof_manifest"],
            self.template["capture"]["visual_proof_board"],
            self.template["creative_contracts"]["implementation_authorization"],
            self.template["creative_contracts"]["owner_transition_correction"],
            self.template["creative_contracts"]["active_creative_contract"],
            self.template["creative_contracts"]["active_transition_timeline"],
            self.template["creative_contracts"]["legacy_v1_contract"],
            self.template["demo_media"]["manifest"],
            self.template["runtime_contracts"]["render_job"],
            self.template["runtime_contracts"]["renderer"],
            self.template["runtime_contracts"]["validator"],
        ]
        self.assertTrue(all((ROOT / path).exists() for path in paths), paths)
        self.assertEqual(self.template["runtime_contracts"]["production_render_plane"], "github_actions")
        self.assertTrue(self.template["runtime_contracts"]["cloudflare_rendering_forbidden"])
        self.assertTrue(self.template["guardrails"]["transitions_only_at_rush_changes"])


if __name__ == "__main__":
    unittest.main()
