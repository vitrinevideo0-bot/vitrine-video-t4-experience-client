from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapter.t4_adapter import build_render_job


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg required")
def test_runtime_capture_manifest_is_built_only_from_verified_media(tmp_path: Path) -> None:
    captures_dir = tmp_path / "captures"
    captures_dir.mkdir()
    durations = {"S1": 6, "S2": 8, "S3": 7, "S4": 9}
    captures: dict[str, dict[str, object]] = {}
    for index, (slot, duration) in enumerate(durations.items(), 1):
        path = captures_dir / f"{slot}.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                f"color=c=0x{index}{index}{index}{index}{index}{index}:s=320x320:r=12:d={duration}",
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path),
            ],
            check=True,
        )
        captures[slot] = {
            "uri": f"rushes/runtime/runtime-visual-test/{slot}.mp4",
            "sha256": sha256(path),
            "mime_type": "video/mp4",
            "width": 320,
            "height": 320,
            "fps": 12,
            "frame_count": duration * 12,
            "duration_ms": duration * 1000,
            "video_codec": "h264",
            "audio_codec": None,
            "has_audio": False,
        }

    job = build_render_job(
        render_job_id="t4-runtime-visual-test-0001",
        merchant_payload={
            "nom": "La Table de Kandi",
            "produit": "Poulet braisé et alloco",
            "prix": "3500",
            "whatsapp": "+229 01 97 00 00 00",
            "quartier": "Kandi, marché central",
            "accroche": "Bien accueillis, bien servis",
        },
        captures=captures,
        control_plane="cloudflare_worker",
    )
    job_path = tmp_path / "job.json"
    manifest_path = tmp_path / "manifest.json"
    visual_job_path = tmp_path / "visual-job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n")
    subprocess.run(
        [
            "python3", "tools/build_t4_runtime_visual_inputs.py",
            "--render-job", str(job_path),
            "--capture-dir", str(captures_dir),
            "--manifest", str(manifest_path),
            "--visual-job", str(visual_job_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(manifest_path.read_text())
    visual_job = json.loads(visual_job_path.read_text())
    assert [scene["duration_seconds"] for scene in manifest["scenes"]] == [6, 8, 7, 9]
    assert [scene["sha256"] for scene in manifest["scenes"]] == [captures[slot]["sha256"] for slot in durations]
    assert visual_job["template_version"] == "3.0.0"
    assert visual_job["provenance"]["control_plane"] == "cloudflare_worker"
