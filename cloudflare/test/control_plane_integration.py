#!/usr/bin/env python3
"""Black-box contract test for a local Wrangler T4 control plane."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
from typing import Any
import urllib.error
import urllib.request

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
MUSIC_IDS = {
    "t4_music_260354",
    "t4_music_154868",
    "t4_music_162186",
    "t4_music_321930",
}
SLOTS = ("S1", "S2", "S3", "S4")


def call(
    base: str,
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    expected: int | tuple[int, ...] = 200,
) -> tuple[bytes, dict[str, str], int]:
    request = urllib.request.Request(base.rstrip("/") + path, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status, payload, response_headers = response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as error:
        status, payload, response_headers = error.code, error.read(), dict(error.headers.items())
    allowed = (expected,) if isinstance(expected, int) else expected
    if status not in allowed:
        raise AssertionError(f"{method} {path}: HTTP {status}, expected {allowed}: {payload.decode(errors='replace')}")
    return payload, response_headers, status


def as_json(payload: bytes) -> dict[str, Any]:
    return json.loads(payload.decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8788")
    parser.add_argument("--client-token", default="test-client")
    parser.add_argument("--callback-token", default="test-callback")
    args = parser.parse_args()

    health = as_json(call(args.base, "/health")[0])
    assert health == {
        "status": "ok",
        "service": "t4-experience-client-control-plane",
        "control_plane": "cloudflare_worker",
        "render_plane": "github_actions",
        "cloudflare_rendering": False,
    }
    form = as_json(call(args.base, "/v1/contracts/form")[0])
    capture_flow = as_json(call(args.base, "/v1/contracts/capture-flow")[0])
    music_pack = as_json(call(args.base, "/v1/contracts/music-pack")[0])
    voice_mix = as_json(call(args.base, "/v1/contracts/voice-mix")[0])
    assert form == json.loads((ROOT / "form/questions_T4.json").read_text())
    assert capture_flow == json.loads((ROOT / "config/T4_CAPTURE_FLOW_V1_0_0.json").read_text())
    assert music_pack == json.loads((ROOT / "config/T4_MUSIC_PACK_V1_0_0.json").read_text())
    assert voice_mix == json.loads((ROOT / "config/T4_VOICE_MIX_V1_0_0.json").read_text())
    assert len(form["fields"]) == 6 and capture_flow["counts"]["stable_capture_screens"] == 12
    assert {track["id"] for track in music_pack["tracks"]} == MUSIC_IDS
    assert voice_mix["voice"]["candidate"] == "VOIX-B" and voice_mix["voice"]["voice_id"] == "voice-07"
    assert "Cloudflare ne réalise jamais le rendu vidéo" in call(args.base, "/")[0].decode("utf-8")

    client_auth = {"authorization": f"Bearer {args.client_token}"}
    callback_auth = {"authorization": f"Bearer {args.callback_token}"}
    merchant_payload = {
        "nom": "La Table de Kandi",
        "produit": "Poulet braisé et alloco",
        "prix": "3500",
        "whatsapp": "+229 01 97 00 00 00",
        "quartier": "Kandi, marché central",
        "accroche": "Bien accueillis, bien servis",
    }
    media = b"t4-control-plane-integration-media"
    media_sha = hashlib.sha256(media).hexdigest()
    rendered_output = b"t4-complete-rendered-mp4-integration-fixture"
    rendered_output_sha = hashlib.sha256(rendered_output).hexdigest()

    unauthorized = as_json(call(args.base, "/v1/jobs", method="POST", body=b"{}", headers={"content-type": "application/json"}, expected=401)[0])
    assert unauthorized["code"] == "T4_UNAUTHORIZED"

    def create_job(music_id: str = "auto") -> tuple[str, str]:
        idem = f"integration-{time.time_ns()}"
        body = json.dumps({"merchant_payload": merchant_payload, "music_id": music_id}, ensure_ascii=False).encode()
        headers = {**client_auth, "content-type": "application/json", "idempotency-key": idem}
        created = as_json(call(args.base, "/v1/jobs", method="POST", body=body, headers=headers, expected=201)[0])
        assert created["status"] == "UPLOADING" and created["required_captures"] == list(SLOTS)
        replay = as_json(call(args.base, "/v1/jobs", method="POST", body=body, headers=headers)[0])
        assert replay == {"job_id": created["job_id"], "status": "UPLOADING", "idempotent_replay": True}
        return created["job_id"], idem

    def upload_all(job_id: str) -> None:
        for slot, duration, frames in (("S1", 6000, 180), ("S2", 8000, 240), ("S3", 7000, 210), ("S4", 9000, 270)):
            webm = slot == "S1"
            headers = {
                **client_auth,
                "content-type": "video/webm" if webm else "video/mp4",
                "content-length": str(len(media)),
                "x-content-sha256": media_sha,
                "x-video-width": "1080",
                "x-video-height": "1920",
                "x-video-fps": "30",
                "x-video-frames": str(frames),
                "x-video-duration-ms": str(duration),
                "x-video-codec": "vp8" if webm else "h264",
                "x-has-audio": "true",
                "x-audio-codec": "opus" if webm else "aac",
            }
            uploaded = as_json(call(args.base, f"/v1/jobs/{job_id}/captures/{slot}", method="PUT", body=media, headers=headers, expected=201)[0])
            assert uploaded["sha256"] == media_sha
        assert uploaded["status"] == "READY"

    def upload_output(job_id: str) -> None:
        stored = as_json(call(
            args.base,
            f"/v1/jobs/{job_id}/output",
            method="PUT",
            body=rendered_output,
            headers={
                **callback_auth,
                "content-type": "video/mp4",
                "content-length": str(len(rendered_output)),
                "x-content-sha256": rendered_output_sha,
            },
            expected=201,
        )[0])
        assert stored["output"]["sha256"] == rendered_output_sha
        payload, headers, _ = call(args.base, f"/v1/jobs/{job_id}/output", headers=callback_auth)
        assert payload == rendered_output and headers["x-content-sha256"] == rendered_output_sha

    job_id, nonce = create_job()
    unsupported = as_json(call(
        args.base,
        f"/v1/jobs/{job_id}/captures/S1",
        method="PUT",
        body=b"test",
        headers={**client_auth, "content-type": "application/octet-stream", "content-length": "4", "x-content-sha256": hashlib.sha256(b"test").hexdigest()},
        expected=415,
    )[0])
    assert unsupported["code"] == "T4_UNSUPPORTED_MEDIA"
    upload_all(job_id)
    assert as_json(call(args.base, f"/v1/jobs/{job_id}/dispatch", method="POST", headers=client_auth, expected=202)[0]) == {"job_id": job_id, "status": "QUEUED"}
    job = as_json(call(args.base, f"/v1/jobs/{job_id}/payload", headers=callback_auth)[0])["job"]
    Draft202012Validator(json.loads((ROOT / "schemas/T4_render_job.schema.json").read_text())).validate(job)
    assert job["merchant_payload"] == merchant_payload
    assert job["control_plane"] == "cloudflare_worker" and job["cloudflare_rendering_forbidden"] is True
    assert job["render"]["production_render_plane"] == "github_actions"
    assert job["music"]["selected_music_id"] in MUSIC_IDS
    assert job["music"]["last_successful_music_id"] is None
    assert job["music"]["state_update_policy"] == "after_completed_qc_pass_only"
    assert job["music"]["content_id_registered"] is False
    assert job["music"]["claim_management_required"] is False
    assert job["voice"]["candidate"] == "VOIX-B" and job["voice"]["voice_id"] == "voice-07"
    assert [placement["start_s"] for placement in job["voice"]["placements"]] == [1.2, 6.8, 14.7, 21.8]
    for slot in SLOTS:
        payload, headers, _ = call(args.base, f"/v1/jobs/{job_id}/captures/{slot}", headers=callback_auth)
        assert payload == media and headers["x-content-sha256"] == media_sha
    upload_output(job_id)

    invalid = as_json(call(
        args.base,
        f"/v1/jobs/{job_id}/events",
        method="POST",
        body=json.dumps({"status": "COMPLETED", "result": {"job_id": "wrong"}}).encode(),
        headers={**callback_auth, "content-type": "application/json"},
        expected=422,
    )[0])
    assert invalid["code"] == "T4_INVALID_CALLBACK_PAYLOAD"

    result_schema = json.loads((ROOT / "schemas/T4_render_result.schema.json").read_text())
    error_schema = json.loads((ROOT / "schemas/T4_render_error.schema.json").read_text())

    def result_for(prepared_id: str, idem: str, prepared_job: dict[str, Any]) -> dict[str, Any]:
        result = {
            "schema_version": "1.0.0",
            "status": "COMPLETED",
            "job_id": prepared_id,
            "idempotency_key": idem,
            "template_id": "RESTAURATION-T4",
            "template_version": "4.0.0-complete-audio",
            "profile_used": "T4_GITHUB_ACTIONS_COMPLETE_V1",
            "control_plane": "cloudflare_worker",
            "output": {
                "uri": f"output/runtime/{prepared_id}/VIDEO_T4_COMPLETE_VOIX_B_MUSIQUE_ROTATION_V4_A_VALIDER.mp4",
                "file": "VIDEO_T4_COMPLETE_VOIX_B_MUSIQUE_ROTATION_V4_A_VALIDER.mp4",
                "sha256": rendered_output_sha,
                "bytes": len(rendered_output),
            },
            "quality": {"status": "PASS", "report": "T4_COMPLETE_RENDER_REPORT.json", "passed": 25, "total": 25},
            "inputs": {
                "music_source_sha256": prepared_job["music"]["source_sha256"],
                "music_derivative_sha256": prepared_job["music"]["sha256"],
                "voice_stem_sha256": prepared_job["voice"]["stem_sha256"],
                "visual_video_bitstream_sha256": "e" * 64,
                "approved_visual_reference_bitstream_sha256": prepared_job["render"]["visual_video_bitstream_sha256"],
                "capture_sha256": {slot: media_sha for slot in SLOTS},
            },
            "music_state_commit_allowed": True,
        }
        Draft202012Validator(result_schema).validate(result)
        return result

    result = result_for(job_id, nonce, job)
    wrong_music = json.loads(json.dumps(result))
    wrong_music["inputs"]["music_source_sha256"] = "0" * 64
    mismatch = as_json(call(
        args.base,
        f"/v1/jobs/{job_id}/events",
        method="POST",
        body=json.dumps({"status": "COMPLETED", "result": wrong_music}).encode(),
        headers={**callback_auth, "content-type": "application/json"},
        expected=422,
    )[0])
    assert mismatch["code"] == "T4_INVALID_CALLBACK_PAYLOAD"

    event = {"status": "COMPLETED", "github_run_id": "123", "github_run_url": "https://github.com/example/actions/runs/123", "result": result}
    assert as_json(call(args.base, f"/v1/jobs/{job_id}/events", method="POST", body=json.dumps(event).encode(), headers={**callback_auth, "content-type": "application/json"})[0]) == {"job_id": job_id, "status": "COMPLETED"}
    # Successful callback replay is a no-op for the rotation state.
    assert as_json(call(args.base, f"/v1/jobs/{job_id}/events", method="POST", body=json.dumps(event).encode(), headers={**callback_auth, "content-type": "application/json"})[0]) == {"job_id": job_id, "status": "COMPLETED"}
    music_state = as_json(call(args.base, "/v1/music-state", headers=callback_auth)[0])
    selected_id = job["music"]["selected_music_id"]
    assert music_state == {
        "schema_version": "1.0.0",
        "last_successful_music_id": selected_id,
        "last_successful_render_job_id": job_id,
        "successful_render_count": 1,
    }

    def prepare(music_id: str, expected_dispatch: int = 202) -> tuple[str, str, dict[str, Any] | None, dict[str, Any]]:
        prepared_id, idem = create_job(music_id)
        upload_all(prepared_id)
        dispatch_payload = as_json(call(args.base, f"/v1/jobs/{prepared_id}/dispatch", method="POST", headers=client_auth, expected=expected_dispatch)[0])
        if expected_dispatch != 202:
            return prepared_id, idem, None, dispatch_payload
        prepared_job = as_json(call(args.base, f"/v1/jobs/{prepared_id}/payload", headers=callback_auth)[0])["job"]
        Draft202012Validator(json.loads((ROOT / "schemas/T4_render_job.schema.json").read_text())).validate(prepared_job)
        upload_output(prepared_id)
        return prepared_id, idem, prepared_job, dispatch_payload

    _, _, _, repeat_error = prepare(selected_id, expected_dispatch=400)
    assert repeat_error["code"] == "T4_INVALID_REQUEST"
    assert as_json(call(args.base, "/v1/music-state", headers=callback_auth)[0]) == music_state

    alternative_id = next(candidate for candidate in MUSIC_IDS if candidate != selected_id)
    failed_id, _, failed_job, _ = prepare(alternative_id)
    assert failed_job and failed_job["music"]["selected_music_id"] == alternative_id
    render_error = {
        "schema_version": "1.0.0",
        "status": "FAILED",
        "job_id": failed_id,
        "code": "T4_UNSUPPORTED_MEDIA",
        "message": "Fixture de test: média non pris en charge.",
        "retryable": False,
        "stage": "VALIDATE_INPUT",
    }
    Draft202012Validator(error_schema).validate(render_error)
    failed_callback = as_json(call(
        args.base,
        f"/v1/jobs/{failed_id}/events",
        method="POST",
        body=json.dumps({"status": "FAILED", "error": render_error}).encode(),
        headers={**callback_auth, "content-type": "application/json"},
    )[0])
    assert failed_callback["status"] == "FAILED"
    assert as_json(call(args.base, "/v1/music-state", headers=callback_auth)[0]) == music_state

    concurrent_jobs = [prepare(alternative_id), prepare(alternative_id)]

    def complete_concurrently(prepared: tuple[str, str, dict[str, Any] | None, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
        prepared_id, idem, prepared_job, _ = prepared
        assert prepared_job is not None
        concurrent_event = {
            "status": "COMPLETED",
            "github_run_id": prepared_id,
            "github_run_url": f"https://github.com/example/actions/runs/{prepared_id}",
            "result": result_for(prepared_id, idem, prepared_job),
        }
        payload, _, status = call(
            args.base,
            f"/v1/jobs/{prepared_id}/events",
            method="POST",
            body=json.dumps(concurrent_event).encode(),
            headers={**callback_auth, "content-type": "application/json"},
            expected=(200, 409),
        )
        return status, as_json(payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent_results = list(executor.map(complete_concurrently, concurrent_jobs))
    assert sorted(status for status, _ in concurrent_results) == [200, 409], concurrent_results
    conflict = next(payload for status, payload in concurrent_results if status == 409)
    assert conflict["code"] == "T4_MUSIC_STATE_CONFLICT"
    final_state = as_json(call(args.base, "/v1/music-state", headers=callback_auth)[0])
    assert final_state["last_successful_music_id"] == alternative_id
    assert final_state["successful_render_count"] == 2
    print("T4_CLOUDFLARE_CONTROL_PLANE_INTEGRATION_OK", job_id)


if __name__ == "__main__":
    main()
