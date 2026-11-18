from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.t4_adapter import (
    EXPECTED_VARIANTS,
    MusicRepeatError,
    approved_tracks,
    build_render_job,
    load_music_selection_state,
    record_music_render_result,
    select_music_variant,
)


def merchant() -> dict[str, str]:
    return {
        "nom": "La Table de Kandi",
        "produit": "Poulet braisé et alloco",
        "prix": "3500",
        "whatsapp": "+229 01 97 00 00 00",
        "quartier": "Kandi, marché central",
        "accroche": "Bien accueillis, bien servis",
    }


def captures() -> dict[str, dict[str, str]]:
    return {slot: {"source": f"rushes/manifest.json#{slot}"} for slot in ("S1", "S2", "S3", "S4")}


def test_exact_owner_approved_pool_and_strict_cycle_selection() -> None:
    tracks = approved_tracks()
    assert [track["id"] for track in tracks] == EXPECTED_VARIANTS
    assert len(tracks) == 4
    assert all(track["content_id_registered"] is False for track in tracks)
    assert all(track["claim_management_required"] is False for track in tracks)
    last = None
    observed = []
    for index in range(40):
        selected = select_music_variant(f"rotation-job-{index}", last)
        observed.append(selected["id"])
        assert selected["selection_mode"] == "strict_success_cycle"
        last = selected["id"]
    assert observed == EXPECTED_VARIANTS * 10


def test_explicit_music_must_be_the_exact_successor() -> None:
    with pytest.raises(MusicRepeatError):
        select_music_variant("explicit-repeat-job", EXPECTED_VARIANTS[0], EXPECTED_VARIANTS[0])
    with pytest.raises(MusicRepeatError):
        select_music_variant("explicit-skip-job", EXPECTED_VARIANTS[0], EXPECTED_VARIANTS[2])
    with pytest.raises(MusicRepeatError):
        select_music_variant("explicit-initial-skip-job", None, EXPECTED_VARIANTS[1])
    with pytest.raises(ValueError):
        select_music_variant("unknown-job", explicit_music_id="not-approved")
    selected = select_music_variant("explicit-ok-job", EXPECTED_VARIANTS[0], EXPECTED_VARIANTS[1])
    assert selected["id"] == EXPECTED_VARIANTS[1]
    assert selected["selection_mode"] == "explicit"


def test_state_advances_only_after_completed_qc_pass_and_is_idempotent(tmp_path: Path) -> None:
    state_path = tmp_path / "music-state.json"
    initial = load_music_selection_state(state_path)
    assert initial["last_successful_music_id"] is None

    failed = record_music_render_result(
        state_path=state_path,
        render_job_id="state-failed-job",
        selected_music_id=EXPECTED_VARIANTS[0],
        completed=False,
        quality_status="FAIL",
    )
    assert failed == initial and not state_path.exists()

    qc_failed = record_music_render_result(
        state_path=state_path,
        render_job_id="state-qc-failed-job",
        selected_music_id=EXPECTED_VARIANTS[0],
        completed=True,
        quality_status="FAIL",
    )
    assert qc_failed == initial and not state_path.exists()

    committed = record_music_render_result(
        state_path=state_path,
        render_job_id="state-success-job",
        selected_music_id=EXPECTED_VARIANTS[0],
        completed=True,
        quality_status="PASS",
    )
    assert committed["successful_render_count"] == 1
    assert committed["last_successful_music_id"] == EXPECTED_VARIANTS[0]
    assert committed["successful_render_jobs"] == {"state-success-job": EXPECTED_VARIANTS[0]}

    replay = record_music_render_result(
        state_path=state_path,
        render_job_id="state-success-job",
        selected_music_id=EXPECTED_VARIANTS[0],
        completed=True,
        quality_status="PASS",
    )
    assert replay == committed

    with pytest.raises(ValueError):
        record_music_render_result(
            state_path=state_path,
            render_job_id="state-success-job",
            selected_music_id=EXPECTED_VARIANTS[1],
            completed=True,
            quality_status="PASS",
        )
    with pytest.raises(MusicRepeatError):
        record_music_render_result(
            state_path=state_path,
            render_job_id="state-new-job-same-music",
            selected_music_id=EXPECTED_VARIANTS[0],
            completed=True,
            quality_status="PASS",
        )

    advanced = record_music_render_result(
        state_path=state_path,
        render_job_id="state-second-success-job",
        selected_music_id=EXPECTED_VARIANTS[1],
        completed=True,
        quality_status="PASS",
    )
    assert advanced["successful_render_count"] == 2
    assert advanced["last_successful_music_id"] == EXPECTED_VARIANTS[1]
    assert len(advanced["successful_render_jobs"]) == 2


def test_old_success_replay_after_full_cycle_is_idempotent(tmp_path: Path) -> None:
    state_path = tmp_path / "full-cycle-state.json"
    for index, selected in enumerate(EXPECTED_VARIANTS, 1):
        record_music_render_result(
            state_path=state_path,
            render_job_id=f"full-cycle-job-{index:04d}",
            selected_music_id=selected,
            completed=True,
            quality_status="PASS",
        )
    after_cycle = load_music_selection_state(state_path)
    replayed = record_music_render_result(
        state_path=state_path,
        render_job_id="full-cycle-job-0001",
        selected_music_id=EXPECTED_VARIANTS[0],
        completed=True,
        quality_status="PASS",
    )
    assert replayed == after_cycle
    assert replayed["successful_render_count"] == 4
    assert replayed["last_successful_music_id"] == EXPECTED_VARIANTS[3]
    assert len(replayed["successful_render_jobs"]) == 4
    with pytest.raises(ValueError):
        record_music_render_result(
            state_path=state_path,
            render_job_id="full-cycle-job-0001",
            selected_music_id=EXPECTED_VARIANTS[1],
            completed=True,
            quality_status="PASS",
        )
    state_schema = json.loads((ROOT / "schemas/T4_music_selection_state.schema.json").read_text())
    Draft202012Validator(state_schema).validate(replayed)


def test_concurrent_successes_cannot_commit_the_same_music_twice(tmp_path: Path) -> None:
    state_path = tmp_path / "concurrent-state.json"

    def commit(job_id: str) -> str:
        try:
            record_music_render_result(
                state_path=state_path,
                render_job_id=job_id,
                selected_music_id=EXPECTED_VARIANTS[0],
                completed=True,
                quality_status="PASS",
            )
            return "committed"
        except MusicRepeatError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(commit, ("concurrent-job-alpha", "concurrent-job-bravo")))
    assert sorted(outcomes) == ["committed", "rejected"]
    state = load_music_selection_state(state_path)
    assert state["successful_render_count"] == 1
    assert len(state["successful_render_jobs"]) == 1


def test_complete_render_job_is_schema_valid_and_locks_voice_visual_mix() -> None:
    job = build_render_job(
        render_job_id="t4-complete-schema-test-0001",
        merchant_payload=merchant(),
        captures=captures(),
        last_successful_music_id=EXPECTED_VARIANTS[0],
        control_plane="cloudflare_worker",
    )
    schema = json.loads((ROOT / "schemas/T4_render_job.schema.json").read_text())
    Draft202012Validator(schema).validate(job)
    assert job["music"]["selected_music_id"] != EXPECTED_VARIANTS[0]
    assert job["music"]["state_update_policy"] == "after_completed_qc_pass_only"
    assert job["voice"]["candidate"] == "VOIX-B"
    assert job["voice"]["voice_id"] == "voice-07"
    assert [item["start_s"] for item in job["voice"]["placements"]] == [1.2, 6.8, 14.7, 21.8]
    assert job["render"]["visual_mode"] == "runtime_hybrid_render"
    assert job["render"]["visual_reencode_forbidden"] is False
    assert job["render"]["audio_mux_video_reencode_forbidden"] is True
    assert job["render"]["production_render_plane"] == "github_actions"
    assert job["cloudflare_rendering_forbidden"] is True
