from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_golden_conformance_contract_hashes_are_current_and_master_is_pending() -> None:
    golden = json.loads((ROOT / "conformance/T4_GOLDEN_V1.json").read_text())
    for relative, expected in golden["contracts"].items():
        assert sha256(ROOT / relative) == expected
    assert golden["complete_master"]["status"] == "pending"
    assert golden["complete_master"]["file_sha256"] is None


def test_integrator_package_spec_paths_exist_and_have_unique_roles() -> None:
    spec = json.loads((ROOT / "packages/t4-experience-client-v1/package_spec.json").read_text())
    paths = [item["path"] for item in spec["include"]]
    assert len(paths) == len(set(paths))
    assert all((ROOT / path).exists() for path in paths)
    assert spec["constraints"]["deterministic_zip"] is True
    assert spec["constraints"]["full_pixabay_originals_forbidden"] is True
    assert spec["constraints"]["cloudflare_deployed"] is False


def test_integrator_builder_refuses_to_package_before_server_master_lock(tmp_path: Path) -> None:
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
    assert "GitHub complete master must be locked first" in result.stderr
    assert list(tmp_path.iterdir()) == []
