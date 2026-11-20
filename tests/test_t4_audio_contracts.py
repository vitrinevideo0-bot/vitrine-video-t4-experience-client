from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checksum_file(directory: Path) -> None:
    for line in (directory / "SHA256SUMS.txt").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        assert sha256(directory / relative) == expected


def test_voice_and_music_contracts_validate_against_schemas() -> None:
    pairs = (
        ("config/T4_VOICE_MIX_V1_0_0.json", "schemas/T4_voice_mix.schema.json"),
        ("config/T4_MUSIC_PACK_V1_0_0.json", "schemas/T4_music_pack.schema.json"),
        ("audio/voice/t4-voice-candidates-v1/manifest.json", "schemas/T4_voice_candidates.schema.json"),
        ("config/T4_EXPERIENCE_CLIENT_PACKAGE_V1_0_0.json", "schemas/T4_template_package.schema.json"),
        ("packages/t4-experience-client-v1/package_spec.json", "schemas/T4_integrator_package_spec.schema.json"),
        ("demo/render_job_complete_v1_0_0.json", "schemas/T4_render_job.schema.json"),
        ("fixtures/t4-experience-client/render_result.valid.json", "schemas/T4_render_result.schema.json"),
        ("fixtures/t4-experience-client/render_error.unsupported_media.json", "schemas/T4_render_error.schema.json"),
    )
    for data_path, schema_path in pairs:
        data = json.loads((ROOT / data_path).read_text())
        schema = json.loads((ROOT / schema_path).read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
    for schema_path in (
        "schemas/T4_music_selection_state.schema.json",
        "schemas/T4_render_result.schema.json",
        "schemas/T4_render_error.schema.json",
    ):
        Draft202012Validator.check_schema(json.loads((ROOT / schema_path).read_text()))


def test_voice_assets_are_hash_locked_and_owner_selection_is_explicit() -> None:
    voice_dir = ROOT / "audio/voice/t4-voice-v1"
    verify_checksum_file(voice_dir)
    config = json.loads((ROOT / "config/T4_VOICE_MIX_V1_0_0.json").read_text())
    voice = config["voice"]
    assert voice["candidate"] == "VOIX-B" and voice["voice_id"] == "voice-07"
    approval = ROOT / voice["approval"]
    assert approval.name == "APPROBATION_VOIX_B_T4_2026-11-20.json" and approval.is_file()
    decision = json.loads(approval.read_text())
    assert decision["selected_candidate"] == "VOIX-B"
    assert decision["selected_internal_voice_id"] == "voice-07"
    assert decision["decided_on"] == "2026-11-20"
    assert sha256(ROOT / voice["stem_file"]) == voice["stem_sha256"]
    assert voice["stem_sha256"] == "74ec6378ba0b724631793c02c2d3f0308913c1790f6606784e587ccd2e34a759"
    assert [clip["start_s"] for clip in voice["clips"]] == [1.2, 6.8, 14.7, 21.8]
    for clip in voice["clips"]:
        assert sha256(ROOT / clip["source"]) == clip["source_sha256"]
        assert sha256(ROOT / clip["processed"]) == clip["processed_sha256"]


def test_four_comparable_voice_candidates_and_owner_gate_are_locked() -> None:
    directory = ROOT / "audio/voice/t4-voice-candidates-v1"
    verify_checksum_file(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["candidate_count"] == 4 and manifest["same_text_for_all"] is True
    assert [item["candidate"] for item in manifest["candidates"]] == ["VOIX-A", "VOIX-B", "VOIX-C", "VOIX-D"]
    assert [item["internal_voice_id"] for item in manifest["candidates"]] == ["voice-06", "voice-07", "voice-08", "voice-09"]
    assert manifest["owner_gate"]["selected_candidate"] == "VOIX-B"
    assert manifest["owner_gate"]["selected_internal_voice_id"] == "voice-07"
    assert manifest["owner_gate"]["decided_on"] == "2026-11-20"
    for item in manifest["candidates"]:
        assert sha256(directory / item["source_file"]) == item["source_sha256"]
        assert sha256(directory / item["listening_file"]) == item["listening_sha256"]
        assert item["retimed"] is False
        assert abs(item["integrated_lufs"] + 20.0) <= 0.15
        assert item["true_peak_dbtp"] <= -3.0


def test_four_music_derivatives_and_public_evidence_are_hash_locked() -> None:
    music_dir = ROOT / "audio/music/t4-afrobeat-v1"
    verify_checksum_file(music_dir)
    config = json.loads((ROOT / "config/T4_MUSIC_PACK_V1_0_0.json").read_text())
    manifest = json.loads((music_dir / "source_manifest.json").read_text())
    tracks = config["tracks"]
    assert len(tracks) == len(manifest["tracks"]) == 4
    assert [track["choice"] for track in tracks] == ["1", "2", "3", "4"]
    assert [track["pixabay_id"] for track in tracks] == [569473, 153058, 573648, 439622]
    assert [track["artist"] for track in tracks] == ["ARPMedia", "FASSounds", "alex-morgan", "SigmaMusicArt"]
    assert all(track["content_id_registered"] and track["claim_management_required"] for track in tracks)
    for track in tracks:
        derivative = ROOT / track["file"]
        assert derivative.stat().st_size == track["bytes"] == 721196
        assert sha256(derivative) == track["sha256"]
        evidence = track["evidence"]
        html_snapshot = ROOT / evidence["page_html_gzip"]
        screenshot = ROOT / evidence["page_screenshot"]
        assert sha256(html_snapshot) == evidence["page_html_sha256"]
        assert sha256(screenshot) == evidence["page_screenshot_sha256"]
        page_text = gzip.decompress(html_snapshot.read_bytes()).decode("utf-8", errors="replace")
        assert "Content ID Registered" in page_text
        assert evidence["official_account_download_certificate_archived"] is False


def test_internal_provenance_certificate_is_explicitly_not_a_pixabay_certificate() -> None:
    path = ROOT / "audio/music/t4-afrobeat-v1/evidence/T4_MUSIC_PROVENANCE_CERTIFICATE.json"
    certificate = json.loads(path.read_text())
    assert certificate["status"] == "PASS"
    assert certificate["issuer_is_pixabay"] is False
    assert certificate["official_pixabay_account_certificate_archived"] is False
    assert len(certificate["records"]) == 4
    source_manifest = ROOT / certificate["source_manifest_file"]
    license_snapshot = ROOT / certificate["license_snapshot_file"]
    assert source_manifest.name == "source_manifest.json"
    assert license_snapshot.name == "PIXABAY_CONTENT_LICENSE_SNAPSHOT_2026-11-20.md"
    assert sha256(source_manifest) == certificate["source_manifest_sha256"]
    assert sha256(license_snapshot) == certificate["license_snapshot_sha256"]
    assert all(record["content_id_registered"] for record in certificate["records"])


def test_effective_voice_music_dates_are_2026_11_20() -> None:
    files = (
        "approvals/APPROBATION_VOIX_B_T4_2026-11-20.json",
        "config/T4_VOICE_MIX_V1_0_0.json",
        "config/T4_MUSIC_PACK_V1_0_0.json",
        "audio/voice/t4-voice-v1/manifest.json",
        "audio/voice/t4-voice-candidates-v1/manifest.json",
        "audio/music/t4-afrobeat-v1/source_manifest.json",
        "audio/music/t4-afrobeat-v1/BUILD_PROVENANCE.json",
        "audio/music/t4-afrobeat-v1/evidence/PIXABAY_CONTENT_LICENSE_SNAPSHOT_2026-11-20.md",
        "audio/music/t4-afrobeat-v1/evidence/T4_MUSIC_PROVENANCE_CERTIFICATE.json",
        "audio/scripts/build_t4_voice_stem.py",
        "audio/scripts/build_t4_music_pack.py",
    )
    for relative in files:
        text = (ROOT / relative).read_text()
        assert "2026-11-18" not in text, relative
        assert "2026-11-20" in text, relative
    assert not (ROOT / "approvals/APPROBATION_VOIX_B_T4_2026-11-18.json").exists()
    assert not (ROOT / "audio/music/t4-afrobeat-v1/evidence/PIXABAY_CONTENT_LICENSE_SNAPSHOT_2026-11-18.md").exists()


def test_canonical_package_references_exist_and_pending_gates_are_honest() -> None:
    canonical = json.loads((ROOT / "config/T4_EXPERIENCE_CLIENT_PACKAGE_V1_0_0.json").read_text())
    paths = [
        canonical["merchant_payload"]["contract"],
        canonical["capture"]["guide"],
        canonical["capture"]["flow"],
        canonical["capture"]["simulation"],
        *canonical["creative_contracts"].values(),
        canonical["runtime_contracts"]["adapter"],
        canonical["runtime_contracts"]["render_job_schema"],
        canonical["runtime_contracts"]["render_result_schema"],
        canonical["runtime_contracts"]["render_error_schema"],
        canonical["runtime_contracts"]["music_selection_state_schema"],
        canonical["runtime_contracts"]["cloudflare_worker"],
        canonical["runtime_contracts"]["workflow"],
        canonical["catalogue_preparation"]["package_spec"],
    ]
    # transition_policy and final_s4_stable_tail_s are values, not paths.
    paths = [path for path in paths if isinstance(path, str) and ("/" in path or path.startswith("."))]
    missing = [path for path in paths if not (ROOT / path).exists()]
    assert missing == []
    assert canonical["complete_audio"]["github_production_master_status"] == "pending"
    assert canonical["known_protocol_deviations"]
    status = json.loads((ROOT / "STATUS.json").read_text())
    assert status["workflow"]["completion_percent_claimed"] is None
    assert status["integration_claims"]["cloudflare_deployed"] is False
    spec = json.loads((ROOT / "packages/t4-experience-client-v1/package_spec.json").read_text())
    assert spec["external_complete_master"]["status"] == "pending_github_render"
    assert spec["external_complete_master"]["sha256"] is None


def test_cloudflare_generated_contracts_are_current() -> None:
    result = subprocess.run(
        ["python3", "tools/build_t4_cloudflare_contracts.py", "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "T4_CLOUDFLARE_CONTRACTS_CURRENT" in result.stdout
