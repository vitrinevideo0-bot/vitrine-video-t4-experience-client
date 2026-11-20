from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_golden_conformance_contract_hashes_are_current_and_master_is_locked() -> None:
    golden = json.loads((ROOT / "conformance/T4_GOLDEN_V1.json").read_text())
    for relative, expected in golden["contracts"].items():
        assert sha256(ROOT / relative) == expected
    complete = golden["complete_master"]
    assert golden["status"] == "github_complete_master_locked"
    assert complete["status"] == "locked_from_additive_release"
    assert complete["release_tag"] == "t4-experience-client-v4.0.0-complete-candidate-1"
    assert complete["file_sha256"] == "b5393c641ddb260167e86858779f2a9b494d789befb081ec3f386d9cda058a1a"
    assert complete["bytes"] == 12126957
    assert complete["video_bitstream_sha256"] == golden["visual"]["approved_video_bitstream_sha256"]
    assert complete["quality"] == {"status": "PASS", "passed": 26, "total": 26}


def test_integrator_package_spec_paths_exist_and_have_unique_roles() -> None:
    spec = json.loads((ROOT / "packages/t4-experience-client-v1/package_spec.json").read_text())
    paths = [item["path"] for item in spec["include"]]
    assert len(paths) == len(set(paths))
    assert all((ROOT / path).exists() for path in paths)
    assert spec["constraints"]["deterministic_zip"] is True
    assert spec["constraints"]["full_pixabay_originals_forbidden"] is True
    assert spec["constraints"]["cloudflare_deployed"] is False


def test_integrator_builder_refuses_a_master_that_does_not_match_the_server_lock(tmp_path: Path) -> None:
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
    assert "complete golden master hash or size mismatch" in result.stderr
    assert list(tmp_path.iterdir()) == []
