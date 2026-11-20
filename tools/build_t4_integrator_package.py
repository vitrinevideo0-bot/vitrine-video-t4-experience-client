#!/usr/bin/env python3
"""Build a deterministic, offline RESTAURATION-T4 integrator ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zipfile

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", ".git", ".tmp",
    ".wrangler", ".wrangler-dry-run", "output", "release", "github-release",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".part", ".DS_Store"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stream_hash(path: Path) -> str:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "hash", "-hash", "sha256", "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("=", 1)[1].lower()


def allowed(relative: Path) -> bool:
    return not (set(relative.parts) & EXCLUDED_PARTS) and relative.suffix not in EXCLUDED_SUFFIXES and relative.name not in {".env", ".dev.vars"}


def expand(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(item for item in path.rglob("*") if item.is_file() and allowed(item.relative_to(ROOT)))
    raise FileNotFoundError(path)


def deterministic_zip(source_root: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source_root.rglob("*") if item.is_file()):
            relative = path.relative_to(source_root.parent).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=ROOT / "packages/t4-experience-client-v1/package_spec.json")
    parser.add_argument("--golden-master", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas/T4_integrator_package_spec.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(spec)
    if spec["status"] != "source_spec_ready_for_deterministic_build":
        raise SystemExit("T4 package spec is not ready: the GitHub complete master must be locked first")
    golden = spec["external_complete_master"]
    if not args.golden_master.is_file():
        raise SystemExit("T4 complete golden master is missing")
    if sha256(args.golden_master) != golden["sha256"] or args.golden_master.stat().st_size != golden["bytes"]:
        raise SystemExit("T4 complete golden master hash or size mismatch")
    actual_stream_hash = stream_hash(args.golden_master)
    if actual_stream_hash != golden["video_bitstream_sha256"]:
        raise SystemExit("T4 complete golden master video bitstream mismatch")

    source_manifest = json.loads((ROOT / "audio/music/t4-afrobeat-v1/source_manifest.json").read_text(encoding="utf-8"))
    original_names = {item["source"]["cache_filename"] for item in source_manifest["tracks"]}
    package_id = spec["package_id"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = args.output_dir / f"{package_id}.zip"
    report_path = args.output_dir / "T4_INTEGRATOR_PACKAGE_BUILD_REPORT.json"

    with tempfile.TemporaryDirectory(prefix="t4-package-") as temporary_name:
        package_root = Path(temporary_name) / package_id
        package_root.mkdir()
        entries: dict[str, dict] = {}
        for item in spec["include"]:
            source = ROOT / item["path"]
            for file_path in expand(source):
                relative = file_path.relative_to(ROOT)
                if file_path.name in original_names:
                    raise RuntimeError(f"Full Pixabay original forbidden: {file_path.name}")
                if not allowed(relative):
                    raise RuntimeError(f"Forbidden package path: {relative}")
                target = package_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_path, target)
                key = relative.as_posix()
                if key in entries:
                    raise RuntimeError(f"Duplicate package path: {key}")
                entries[key] = {"path": key, "role": item["role"], "bytes": target.stat().st_size, "sha256": sha256(target)}

        golden_target = package_root / golden["package_path"]
        golden_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.golden_master, golden_target)
        entries[golden["package_path"]] = {
            "path": golden["package_path"],
            "role": "golden_complete_master",
            "bytes": golden_target.stat().st_size,
            "sha256": sha256(golden_target),
            "video_bitstream_sha256": actual_stream_hash,
        }
        manifest = {
            "schema_version": "1.0.0",
            "package_id": package_id,
            "template_id": "RESTAURATION-T4",
            "template_version": spec["template_version"],
            "status": "READY_FOR_INTEGRATOR",
            "source_spec": args.spec.relative_to(ROOT).as_posix(),
            "source_spec_sha256": sha256(args.spec),
            "deterministic_zip_timestamp": "1980-01-01T00:00:00Z",
            "entries": [entries[key] for key in sorted(entries)],
            "entry_count": len(entries),
            "constraints": spec["constraints"],
            "external_complete_master": golden,
        }
        (package_root / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        deterministic_zip(package_root, zip_path)

    report = {
        "schema_version": "1.0.0",
        "template_id": "RESTAURATION-T4",
        "status": "PASS",
        "package_id": package_id,
        "zip": {"file": zip_path.name, "bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
        "entry_count": len(entries),
        "golden_master": {"sha256": golden["sha256"], "bytes": golden["bytes"], "video_bitstream_sha256": actual_stream_hash},
        "full_pixabay_originals_included": False,
        "standalone_music_release_assets_created": False,
        "secrets_injected": False,
        "cloudflare_deployed": False,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "SHA256SUMS.txt").write_text(
        f"{sha256(zip_path)}  {zip_path.name}\n{sha256(report_path)}  {report_path.name}\n",
        encoding="utf-8",
    )
    print(f"T4_INTEGRATOR_PACKAGE_PASS {zip_path} {sha256(zip_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
