#!/usr/bin/env python3
"""T4 adapter, deterministic four-track rotation and success-only state commit."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MUSIC_PACK = ROOT / "config/T4_MUSIC_PACK_V1_0_0.json"
VOICE_MIX = ROOT / "config/T4_VOICE_MIX_V1_0_0.json"
MUSIC_STATE_SCHEMA_VERSION = "1.0.0"
EXPECTED_VARIANTS = [
    "t4_music_260354",
    "t4_music_154868",
    "t4_music_162186",
    "t4_music_321930",
]
EXPECTED_PIXABAY_IDS = [260354, 154868, 162186, 321930]


class MusicRepeatError(ValueError):
    """Raised when a selection or successful commit violates the strict cycle."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def approved_tracks(music_pack_path: Path = MUSIC_PACK) -> list[dict[str, Any]]:
    pack = load_json(music_pack_path)
    tracks = list(pack.get("tracks", []))
    variants = list(pack.get("selection_contract", {}).get("owner_approved_variant_ids", []))
    if len(tracks) != 4 or variants != EXPECTED_VARIANTS:
        raise ValueError("T4 requires exactly the four owner-approved music variants in locked order")
    if [track.get("id") for track in tracks] != EXPECTED_VARIANTS:
        raise ValueError("T4 music IDs diverge from the owner-approved order")
    if [track.get("pixabay_id") for track in tracks] != EXPECTED_PIXABAY_IDS:
        raise ValueError("T4 Pixabay IDs diverge from the owner-approved pool")
    if any(not track.get("audition_approved_by_owner") or not track.get("production_eligible") for track in tracks):
        raise ValueError("Every T4 music variant must be owner-approved and production-eligible")
    if any(track.get("content_id_registered") is not False for track in tracks):
        raise ValueError("T4 replacement tracks must have no Content ID Registered label in the dated evidence")
    if any(track.get("claim_management_required") is not False for track in tracks):
        raise ValueError("T4 replacement tracks must not require Content ID claim management")
    contract = pack["selection_contract"]
    if (
        contract.get("automatic_algorithm") != "strict owner-approved order 1→2→3→4→1 from last successful music"
        or contract.get("no_immediate_repeat") is not True
        or contract.get("explicit_selection_policy") != "exact_successor_only"
        or contract.get("first_render_pool_size") != 1
        or contract.get("subsequent_pool_size") != 1
        or contract.get("idempotency_ledger_key") != "successful_render_jobs"
        or contract.get("state_update_policy") != "after_completed_qc_pass_only"
        or contract.get("failed_render_state_policy") != "unchanged"
    ):
        raise ValueError("T4 music contract must enforce the exact success cycle and durable idempotency")
    return tracks


def select_music_variant(
    render_job_id: str,
    last_successful_music_id: str | None = None,
    explicit_music_id: str | None = None,
    music_pack_path: Path = MUSIC_PACK,
) -> dict[str, Any]:
    """Select one track in the strict owner-approved 1 → 2 → 3 → 4 cycle."""
    if not render_job_id:
        raise ValueError("render_job_id is required")
    tracks = approved_tracks(music_pack_path)
    by_id = {track["id"]: track for track in tracks}
    if last_successful_music_id is not None and last_successful_music_id not in by_id:
        raise ValueError("Unknown last successful T4 music ID")
    previous_index = -1 if last_successful_music_id is None else EXPECTED_VARIANTS.index(last_successful_music_id)
    selected = tracks[(previous_index + 1) % len(tracks)]
    if explicit_music_id is not None:
        if explicit_music_id not in by_id:
            raise ValueError("Explicit T4 music ID is not owner-approved")
        if explicit_music_id != selected["id"]:
            raise MusicRepeatError(
                f"Strict T4 cycle expects {selected['id']}; {explicit_music_id} cannot bypass it"
            )
        return {**selected, "selection_mode": "explicit", "last_successful_music_id": last_successful_music_id}
    return {**selected, "selection_mode": "strict_success_cycle", "last_successful_music_id": last_successful_music_id}


def initial_music_state() -> dict[str, Any]:
    return {
        "schema_version": MUSIC_STATE_SCHEMA_VERSION,
        "last_successful_music_id": None,
        "last_successful_render_job_id": None,
        "successful_render_count": 0,
        "successful_render_jobs": {},
    }


def load_music_selection_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return initial_music_state()
    state = load_json(state_path)
    required = {
        "schema_version",
        "last_successful_music_id",
        "last_successful_render_job_id",
        "successful_render_count",
        "successful_render_jobs",
    }
    if set(state) != required or state["schema_version"] != MUSIC_STATE_SCHEMA_VERSION:
        raise ValueError("Invalid T4 music rotation state")
    if state["last_successful_music_id"] not in {None, *EXPECTED_VARIANTS}:
        raise ValueError("Unknown T4 music ID in persistent state")
    if not isinstance(state["successful_render_count"], int) or state["successful_render_count"] < 0:
        raise ValueError("Invalid T4 successful render count")
    receipts = state["successful_render_jobs"]
    if (
        not isinstance(receipts, dict)
        or any(not isinstance(job_id, str) or not job_id or music_id not in EXPECTED_VARIANTS for job_id, music_id in receipts.items())
        or len(receipts) != state["successful_render_count"]
    ):
        raise ValueError("Invalid T4 successful render ledger")
    if (state["last_successful_music_id"] is None) != (state["last_successful_render_job_id"] is None):
        raise ValueError("T4 state must pair successful music and render job IDs")
    if (state["successful_render_count"] == 0) != (state["last_successful_music_id"] is None):
        raise ValueError("An empty T4 state cannot contain a successful render, and conversely")
    if state["last_successful_render_job_id"] is not None and receipts.get(state["last_successful_render_job_id"]) != state["last_successful_music_id"]:
        raise ValueError("The last T4 success must exist in the idempotency ledger")
    return state


def select_music_variant_from_state(
    render_job_id: str,
    state_path: Path,
    explicit_music_id: str | None = None,
    music_pack_path: Path = MUSIC_PACK,
) -> dict[str, Any]:
    state = load_music_selection_state(state_path)
    return select_music_variant(
        render_job_id,
        state["last_successful_music_id"],
        explicit_music_id,
        music_pack_path,
    )


def _record_music_render_result_unlocked(
    *,
    state_path: Path,
    render_job_id: str,
    selected_music_id: str,
    completed: bool,
    quality_status: str,
    music_pack_path: Path = MUSIC_PACK,
) -> dict[str, Any]:
    """Persist only COMPLETED + PASS, leaving failures and failed QC unchanged."""
    if not render_job_id:
        raise ValueError("render_job_id is required")
    allowed = {track["id"] for track in approved_tracks(music_pack_path)}
    if selected_music_id not in allowed:
        raise ValueError("Rendered T4 music is not owner-approved")
    current = load_music_selection_state(state_path)
    succeeded = completed and quality_status == "PASS"
    if not succeeded:
        return current
    if render_job_id in current["successful_render_jobs"]:
        if current["successful_render_jobs"][render_job_id] != selected_music_id:
            raise ValueError("An idempotent successful callback cannot change T4 music")
        return current
    previous_id = current["last_successful_music_id"]
    expected_id = EXPECTED_VARIANTS[0] if previous_id is None else EXPECTED_VARIANTS[(EXPECTED_VARIANTS.index(previous_id) + 1) % len(EXPECTED_VARIANTS)]
    if selected_music_id != expected_id:
        raise MusicRepeatError(
            f"Successful T4 render must follow the strict cycle: expected {expected_id}, got {selected_music_id}"
        )
    updated = {
        "schema_version": MUSIC_STATE_SCHEMA_VERSION,
        "last_successful_music_id": selected_music_id,
        "last_successful_render_job_id": render_job_id,
        "successful_render_count": current["successful_render_count"] + 1,
        "successful_render_jobs": {**current["successful_render_jobs"], render_job_id: selected_music_id},
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{state_path.name}.", dir=state_path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(updated, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, state_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return updated


def record_music_render_result(
    *,
    state_path: Path,
    render_job_id: str,
    selected_music_id: str,
    completed: bool,
    quality_status: str,
    music_pack_path: Path = MUSIC_PACK,
) -> dict[str, Any]:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.parent / f".{state_path.name}.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            return _record_music_render_result_unlocked(
                state_path=state_path,
                render_job_id=render_job_id,
                selected_music_id=selected_music_id,
                completed=completed,
                quality_status=quality_status,
                music_pack_path=music_pack_path,
            )
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def build_render_job(
    *,
    render_job_id: str,
    merchant_payload: dict[str, str],
    captures: dict[str, dict[str, Any]],
    last_successful_music_id: str | None = None,
    explicit_music_id: str | None = None,
    control_plane: str = "github_actions_manual",
    music_pack_path: Path = MUSIC_PACK,
    voice_mix_path: Path = VOICE_MIX,
) -> dict[str, Any]:
    required_fields = ["nom", "produit", "prix", "whatsapp", "quartier", "accroche"]
    if list(merchant_payload) != required_fields:
        raise ValueError(f"merchant_payload keys must be exactly {required_fields}")
    if list(captures) != ["S1", "S2", "S3", "S4"]:
        raise ValueError("captures must be exactly S1, S2, S3 and S4 in order")
    selected = select_music_variant(render_job_id, last_successful_music_id, explicit_music_id, music_pack_path)
    voice = load_json(voice_mix_path)
    approved = voice["visual_approved"]
    clips = voice["voice"]["clips"]
    runtime_visual = control_plane == "cloudflare_worker"
    return {
        "schema_version": "1.0.0",
        "job_id": render_job_id,
        "idempotency_key": render_job_id,
        "template_id": "RESTAURATION-T4",
        "template_version": "4.0.0-complete-audio",
        "merchant_payload": merchant_payload,
        "captures": captures,
        "music": {
            "selection_mode": selected["selection_mode"],
            "selected_music_id": selected["id"],
            "selected_choice": selected["choice"],
            "pixabay_id": selected["pixabay_id"],
            "file": selected["file"],
            "sha256": selected["sha256"],
            "source_sha256": selected["source_sha256"],
            "content_id_registered": selected["content_id_registered"],
            "claim_management_required": selected["claim_management_required"],
            "last_successful_music_id": last_successful_music_id,
            "state_update_policy": "after_completed_qc_pass_only",
        },
        "voice": {
            "candidate": voice["voice"]["candidate"],
            "voice_id": voice["voice"]["voice_id"],
            "language": voice["voice"]["language"],
            "stem_file": voice["voice"]["stem_file"],
            "stem_sha256": voice["voice"]["stem_sha256"],
            "placements": [
                {"scene": clip["scene"], "start_s": clip["start_s"], "end_s": clip["end_s"], "text": clip["text"]}
                for clip in clips
            ],
        },
        "render": {
            "visual_mode": "runtime_hybrid_render" if runtime_visual else "approved_master_stream_copy",
            "visual_source_role": "approved_design_reference" if runtime_visual else "approved_render_source",
            "visual_source_url": approved["download_url"],
            "visual_source_sha256": approved["file_sha256"],
            "visual_video_bitstream_sha256": approved["video_bitstream_sha256"],
            "visual_reencode_forbidden": not runtime_visual,
            "audio_mux_video_reencode_forbidden": True,
            "runtime_capture_manifest_required": runtime_visual,
            "width": 720,
            "height": 1280,
            "fps": 30,
            "frames": 900,
            "duration_s": 30.0,
            "output_count": 1,
            "output_filename": "VIDEO_T4_COMPLETE_VOIX_B_MUSIQUE_ROTATION_V4_A_VALIDER.mp4",
            "production_render_plane": "github_actions",
        },
        "mix_contract": voice["mix_contract"],
        "control_plane": control_plane,
        "cloudflare_rendering_forbidden": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    select = sub.add_parser("select")
    select.add_argument("--render-job-id", required=True)
    select.add_argument("--last-successful-music-id")
    select.add_argument("--explicit-music-id")

    build = sub.add_parser("build-job")
    build.add_argument("--render-job-id", required=True)
    build.add_argument("--input", type=Path, default=ROOT / "demo/render_job_hybrid_v3.json")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--last-successful-music-id")
    build.add_argument("--explicit-music-id")
    build.add_argument("--control-plane", default="github_actions_manual")

    commit = sub.add_parser("commit")
    commit.add_argument("--state", type=Path, required=True)
    commit.add_argument("--render-job-id", required=True)
    commit.add_argument("--selected-music-id", required=True)
    commit.add_argument("--completed", action="store_true")
    commit.add_argument("--quality-status", default="FAIL")

    args = parser.parse_args()
    if args.command == "select":
        print(json.dumps(select_music_variant(
            args.render_job_id, args.last_successful_music_id, args.explicit_music_id
        ), ensure_ascii=False, indent=2))
        return 0
    if args.command == "build-job":
        source = load_json(args.input)
        job = build_render_job(
            render_job_id=args.render_job_id,
            merchant_payload=source["merchant_payload"],
            captures=source["captures"],
            last_successful_music_id=args.last_successful_music_id,
            explicit_music_id=args.explicit_music_id,
            control_plane=args.control_plane,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status":"READY","output":str(args.output),"music":job["music"]}, ensure_ascii=False, indent=2))
        return 0
    state = record_music_render_result(
        state_path=args.state,
        render_job_id=args.render_job_id,
        selected_music_id=args.selected_music_id,
        completed=args.completed,
        quality_status=args.quality_status,
    )
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
