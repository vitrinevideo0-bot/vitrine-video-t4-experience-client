#!/usr/bin/env python3
"""Validate a clean extraction of a deterministic RESTAURATION-T4 package."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from jsonschema import Draft202012Validator


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def stream_hash(path: Path) -> str:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("=", 1)[1].lower()


def check(name: str, passed: bool, detail: object = None) -> dict:
    return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--proof", type=Path, required=True)
    args = parser.parse_args()
    checks: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="t4-package-validation-") as temporary_name:
        temporary = Path(temporary_name)
        with zipfile.ZipFile(args.zip) as archive:
            unsafe = [name for name in archive.namelist() if name.startswith("/") or ".." in Path(name).parts]
            checks.append(check("zip_paths_safe", not unsafe, unsafe))
            archive.extractall(temporary)
        roots = [path for path in temporary.iterdir() if path.is_dir()]
        checks.append(check("single_package_root", len(roots) == 1, [path.name for path in roots]))
        if len(roots) != 1:
            raise SystemExit("Invalid package root")
        root = roots[0]
        manifest = load(root / "PACKAGE_MANIFEST.json")
        spec = load(root / manifest["source_spec"])
        checks.append(check("package_id_matches", root.name == manifest["package_id"] == spec["package_id"], root.name))
        entries = {item["path"]: item for item in manifest["entries"]}
        extracted_files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
        checks.append(check("manifest_entry_count", manifest["entry_count"] == len(entries), len(entries)))
        checks.append(check("no_unmanifested_files", extracted_files == set(entries) | {"PACKAGE_MANIFEST.json"}, sorted(extracted_files - set(entries) - {"PACKAGE_MANIFEST.json"})))
        bad_hashes = []
        for relative, entry in entries.items():
            path = root / relative
            if not path.is_file() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
                bad_hashes.append(relative)
        checks.append(check("all_manifest_hashes_and_sizes", not bad_hashes, bad_hashes))

        schema_pairs = [
            ("config/T4_EXPERIENCE_CLIENT_PACKAGE_V1_0_0.json", "schemas/T4_template_package.schema.json"),
            ("config/T4_VOICE_MIX_V1_0_0.json", "schemas/T4_voice_mix.schema.json"),
            ("config/T4_MUSIC_PACK_V1_0_0.json", "schemas/T4_music_pack.schema.json"),
            ("audio/voice/t4-voice-candidates-v1/manifest.json", "schemas/T4_voice_candidates.schema.json"),
            ("demo/render_job_complete_v1_0_0.json", "schemas/T4_render_job.schema.json"),
            ("fixtures/t4-experience-client/render_result.valid.json", "schemas/T4_render_result.schema.json"),
            ("fixtures/t4-experience-client/render_error.unsupported_media.json", "schemas/T4_render_error.schema.json"),
            ("packages/t4-experience-client-v1/package_spec.json", "schemas/T4_integrator_package_spec.schema.json"),
        ]
        schema_errors = []
        for data_path, schema_path in schema_pairs:
            try:
                schema = load(root / schema_path)
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(load(root / data_path))
            except Exception as error:  # noqa: BLE001
                schema_errors.append({"data": data_path, "schema": schema_path, "error": str(error)})
        checks.append(check("strict_schemas_validate", not schema_errors, schema_errors))

        questions = load(root / "form/questions_T4.json")
        flow = load(root / "config/T4_CAPTURE_FLOW_V1_0_0.json")
        music = load(root / "config/T4_MUSIC_PACK_V1_0_0.json")
        voice = load(root / "config/T4_VOICE_MIX_V1_0_0.json")
        candidates = load(root / "audio/voice/t4-voice-candidates-v1/manifest.json")
        checks.append(check("six_questions", len(questions["fields"]) == 6))
        checks.append(check("twelve_executable_screens", len(flow["screens"]) == flow["counts"]["stable_capture_screens"] == 12))
        checks.append(check("scene_durations_6_8_7_9", list(flow["scene_durations_ms"].values()) == [6000, 8000, 7000, 9000]))
        checks.append(check("four_owner_approved_afrobeat_tracks", len(music["tracks"]) == 4 and all(track["audition_approved_by_owner"] for track in music["tracks"])))
        checks.append(check("all_music_content_id_disclosed", all(track["content_id_registered"] for track in music["tracks"])))
        checks.append(check("four_comparable_voice_candidates", len(candidates["candidates"]) == 4 and candidates["same_text_for_all"] is True))
        checks.append(check("owner_selected_voice_B", voice["voice"]["candidate"] == candidates["owner_gate"]["selected_candidate"] == "VOIX-B" and voice["voice"]["voice_id"] == "voice-07"))
        checks.append(check("voice_stem_integrity", sha256(root / voice["voice"]["stem_file"]) == voice["voice"]["stem_sha256"]))

        sys.path.insert(0, str(root))
        adapter = importlib.import_module("adapter.t4_adapter")
        variants = adapter.EXPECTED_VARIANTS
        counts = {variant: 0 for variant in variants}
        repeat_ok = True
        last = None
        for index in range(10_000):
            selected = adapter.select_music_variant(f"t4-package-stress-{index:05d}", last)
            repeat_ok &= selected["id"] != last
            counts[selected["id"]] += 1
            last = selected["id"]
        checks.append(check("music_rotation_10000_zero_adjacent_repeat", repeat_ok, counts))
        state_path = temporary / "music-state.json"
        first = adapter.select_music_variant("t4-package-state-0001")["id"]
        adapter.record_music_render_result(state_path=state_path, render_job_id="t4-package-state-failed", selected_music_id=first, completed=False, quality_status="FAIL")
        failure_unchanged = not state_path.exists()
        committed = adapter.record_music_render_result(state_path=state_path, render_job_id="t4-package-state-0001", selected_music_id=first, completed=True, quality_status="PASS")
        second = adapter.select_music_variant("t4-package-state-0002", first)["id"]
        checks.append(check("music_state_success_only_and_no_repeat", failure_unchanged and committed["last_successful_music_id"] == first and second != first, committed))

        golden = spec["external_complete_master"]
        golden_path = root / golden["package_path"]
        checks.append(check("golden_master_hash_and_size", golden_path.is_file() and sha256(golden_path) == golden["sha256"] and golden_path.stat().st_size == golden["bytes"]))
        media = probe(golden_path)
        video = next(stream for stream in media["streams"] if stream.get("codec_type") == "video")
        audio = next(stream for stream in media["streams"] if stream.get("codec_type") == "audio")
        checks.append(check("golden_30s_900_frames_720x1280_30fps", abs(float(media["format"]["duration"]) - 30.0) <= 0.001 and int(video.get("nb_read_frames") or video.get("nb_frames")) == 900 and (video["width"], video["height"], video["r_frame_rate"]) == (720, 1280, "30/1")))
        checks.append(check("golden_aac_stereo_48khz", audio["codec_name"] == "aac" and int(audio["sample_rate"]) == 48000 and int(audio["channels"]) == 2))
        checks.append(check("golden_video_bitstream_locked", stream_hash(golden_path) == golden["video_bitstream_sha256"], stream_hash(golden_path)))

        source_manifest = load(root / "audio/music/t4-afrobeat-v1/source_manifest.json")
        original_names = {track["source"]["cache_filename"] for track in source_manifest["tracks"]}
        packaged_names = {path.name for path in root.rglob("*") if path.is_file()}
        checks.append(check("no_full_pixabay_originals", not (original_names & packaged_names), sorted(original_names & packaged_names)))
        checks.append(check("no_node_modules_or_temporary_state", not any(part in {"node_modules", ".wrangler", ".wrangler-dry-run", ".tmp", "output"} for path in root.rglob("*") for part in path.relative_to(root).parts)))
        forbidden_names = {".env", ".dev.vars", "hosts.yml", "credentials", "credentials.json", ".netrc"}
        checks.append(check("no_secret_files", not any(path.name in forbidden_names for path in root.rglob("*"))))
        token_pattern = re.compile(r"(?:gh[opsu]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|CLOUDFLARE_API_TOKEN\s*=\s*[^$<\s])")
        leaked = []
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".md", ".py", ".yml", ".yaml", ".toml", ".js", ".ts", ".html", ".txt"}:
                if token_pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                    leaked.append(path.relative_to(root).as_posix())
        checks.append(check("no_embedded_secret_values", not leaked, leaked))
        boundary = load(root / "integration-handoff/T4_CLOUDFLARE_BOUNDARY_V1.json")
        checks.append(check("cloudflare_prepared_but_not_falsely_deployed", boundary["local_black_box_integration"] == "PASS" and boundary["cloudflare_deployed"] is False))
        canonical = load(root / "config/T4_EXPERIENCE_CLIENT_PACKAGE_V1_0_0.json")
        checks.append(check("no_known_protocol_deviation_remaining", canonical["known_protocol_deviations"] == [], canonical["known_protocol_deviations"]))

        tests = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        checks.append(check("included_test_suite_passes_after_clean_extraction", tests.returncode == 0, {"returncode": tests.returncode, "output_tail": tests.stdout[-4000:]}))

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    proof = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "status": status,
        "scope": "Clean extraction validation of RESTAURATION-T4 integrator package",
        "zip": {"file": args.zip.name, "bytes": args.zip.stat().st_size, "sha256": sha256(args.zip)},
        "checks": checks,
        "summary": {"passed": sum(item["status"] == "PASS" for item in checks), "failed": sum(item["status"] == "FAIL" for item in checks), "total": len(checks)},
        "strict_universal_protocol_100_percent": status == "PASS",
        "cloudflare_deployed": False,
    }
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    args.proof.write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"T4_INTEGRATOR_PACKAGE_{status} {proof['summary']['passed']}/{proof['summary']['total']} {args.proof}")
    if status != "PASS":
        for item in checks:
            if item["status"] == "FAIL":
                print("FAIL", item["check"], item["detail"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
