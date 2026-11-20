from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_replacement_pool_contract_hashes_and_github_master_are_locked() -> None:
    golden = json.loads((ROOT / "conformance/T4_GOLDEN_V1.json").read_text())
    for relative, expected in golden["contracts"].items():
        assert sha256(ROOT / relative) == expected
    complete = golden["complete_master"]
    assert golden["status"] == "github_replacement_pool_complete_master_locked"
    assert golden["music"]["variant_ids"] == [
        "t4_music_260354", "t4_music_154868", "t4_music_162186", "t4_music_321930"
    ]
    assert complete["status"] == "locked_from_additive_release"
    assert complete["github_run_id"] == "44702885815"
    assert complete["release_tag"] == "t4-experience-client-v4.1.0-pixabay-replacement-candidate-2"
    assert complete["file_sha256"] == "a1cf0abf8f00724468c1489ce14f5e656b3eb85730c5d1e2a4ec383117fe74bd"
    assert complete["bytes"] == 12157788
    assert complete["video_bitstream_sha256"] == golden["visual"]["approved_video_bitstream_sha256"]
    assert complete["selected_music_id"] == "t4_music_162186"
    assert complete["quality"] == {"status": "PASS", "passed": 26, "total": 26}


def test_integrator_package_spec_paths_exist_and_have_unique_roles() -> None:
    spec = json.loads((ROOT / "packages/t4-experience-client-v1/package_spec.json").read_text())
    paths = [item["path"] for item in spec["include"]]
    assert len(paths) == len(set(paths))
    assert all((ROOT / path).exists() for path in paths)
    assert spec["constraints"]["deterministic_zip"] is True
    assert spec["constraints"]["full_pixabay_originals_forbidden"] is True
    assert spec["constraints"]["cloudflare_deployed"] is False


def test_integrator_builder_refuses_an_unlocked_or_tampered_master(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "python3",
            "tools/build_t4_integrator_package.py",
            "--golden-master",
            "README.md",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "golden master hash or size mismatch" in result.stderr
    assert list(tmp_path.iterdir()) == []
