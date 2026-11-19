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
        cls.template = load("config/T4_EXPERIENCE_CLIENT_TEMPLATE_V1_0_0.json")
        cls.creative = load("config/T4_CREATIVE_CONTRACT_V1_0_0.json")
        cls.transitions = load("reverse-engineering/T4_TRANSITIONS_30S.json")
        cls.rushes = load("rushes/manifest.json")
        cls.ui = load("ui-screens/manifest.json")
        cls.job = load("demo/render_job_silent_demo.json")

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

    def test_approved_reference_fusion_is_a_b_c_d(self) -> None:
        self.assertTrue(self.creative["approval_state"]["reference_fusion_owner_approved"])
        self.assertEqual([item["slot"] for item in self.creative["source_references"]], ["A", "B", "C", "D"])
        self.assertEqual(self.creative["creative_fusion"]["structural_base"], "A")
        self.assertEqual(self.creative["creative_fusion"]["tile_choreography"], "B")
        self.assertEqual(self.creative["creative_fusion"]["impact_grammar"], "C")
        self.assertEqual(self.creative["creative_fusion"]["micro_break_grammar"], "D")

    def test_exact_transition_timeline(self) -> None:
        events = self.transitions["timeline_events"]
        self.assertEqual(len(events), 48)
        for left, right in zip(events, events[1:]):
            self.assertLess(left["frames"][1], right["frames"][0])
        families = {event["family"] for event in events}
        self.assertEqual(families, {
            "T4_TILE_REVEAL",
            "T4_DYNAMIC_GRID_RECONFIG",
            "T4_SHAKE_IMPACT",
            "T4_RECTANGULAR_BLOCK_STUTTER",
            "T4_MICRO_GLITCH",
        })
        micro = [event for event in events if event["family"] == "T4_MICRO_GLITCH"]
        self.assertTrue(all(1 <= event["duration_frames"] <= 3 for event in micro))
        self.assertFalse(any(event["frames"][0] <= 899 and event["frames"][1] >= 810 for event in events))
        audit = self.transitions["cadence_audit"]
        self.assertEqual(audit["covered_effect_frames"] + audit["default_stable_frames"], 900)
        self.assertGreaterEqual(audit["default_stable_share"], 0.42)
        self.assertLessEqual(audit["default_stable_share"], 0.58)
        self.assertGreaterEqual(audit["tile_plus_grid_share"], 0.24)
        self.assertLessEqual(audit["tile_plus_grid_share"], 0.38)

    def test_no_blue_cyan_separators_and_no_silent_text(self) -> None:
        owner = self.transitions["owner_constraints"]
        self.assertTrue(owner["blue_or_cyan_separator_lines_forbidden"])
        self.assertTrue(owner["silent_render_text_forbidden"])
        self.assertTrue(owner["silent_render_audio_forbidden"])
        profile = self.transitions["transition_parameter_profiles"]["T4_DYNAMIC_GRID_RECONFIG"]
        self.assertFalse(profile["separator_lines"])
        self.assertIsNone(profile["separator_color"])
        self.assertFalse(self.template["format"]["silent_candidate_burned_text"])
        self.assertEqual(self.template["format"]["silent_candidate_audio_streams"], 0)

    def test_four_licensed_hash_locked_rushes(self) -> None:
        self.assertEqual(len(self.rushes["scenes"]), 4)
        self.assertFalse(self.rushes["license"]["raw_media_committed"])
        self.assertFalse(self.rushes["license"]["raw_media_published_as_artifact"])
        self.assertEqual(len({scene["pexels_id"] for scene in self.rushes["scenes"]}), 4)
        self.assertTrue(all(len(scene["sha256"]) == 64 for scene in self.rushes["scenes"]))
        self.assertTrue(all(scene["source_duration_seconds"] - scene["trim_start_seconds"] >= scene["duration_seconds"] for scene in self.rushes["scenes"]))

    def test_render_job_is_strictly_silent_and_textless(self) -> None:
        self.assertEqual(list(self.job["merchant_payload"]), ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"])
        profile = self.job["render_profile"]
        self.assertFalse(profile["burn_merchant_text"])
        self.assertFalse(profile["include_capture_audio"])
        self.assertFalse(profile["include_music"])
        self.assertFalse(profile["include_voice_over"])
        self.assertFalse(self.job["output"]["audio"])
        self.assertFalse(self.job["output"]["burned_text"])

    def test_all_linked_contract_files_exist(self) -> None:
        paths = [
            self.template["merchant_payload"]["source"],
            self.template["capture"]["guide"],
            self.template["capture"]["flow_contract"],
            self.template["capture"]["visual_proof_manifest"],
            self.template["capture"]["visual_proof_board"],
            self.template["creative_contracts"]["implementation_authorization"],
            self.template["creative_contracts"]["reference_fusion_approval"],
            self.template["creative_contracts"]["creative_contract"],
            self.template["creative_contracts"]["transition_timeline"],
            self.template["demo_media"]["manifest"],
            self.template["runtime_contracts"]["render_job"],
            self.template["runtime_contracts"]["renderer"],
            self.template["runtime_contracts"]["validator"],
        ]
        self.assertTrue(all((ROOT / path).exists() for path in paths), paths)
        self.assertEqual(self.template["runtime_contracts"]["production_render_plane"], "github_actions")
        self.assertTrue(self.template["runtime_contracts"]["cloudflare_rendering_forbidden"])


if __name__ == "__main__":
    unittest.main()
