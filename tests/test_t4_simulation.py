from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_simulation_is_reproducible_and_embeds_6_plus_12(tmp_path: Path) -> None:
    generated = tmp_path / "simulation.html"
    subprocess.run(
        ["python3", "tools/build_t4_simulation.py", "--output", str(generated)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    approved = ROOT / "simulation/T4_12_ECRANS_EXECUTABLE.html"
    assert generated.read_bytes() == approved.read_bytes()
    text = approved.read_text()
    question_match = re.search(r'<script type="application/json" id="questions">(.*?)</script>', text, re.S)
    flow_match = re.search(r'<script type="application/json" id="flow">(.*?)</script>', text, re.S)
    assert question_match and flow_match
    questions = json.loads(question_match.group(1))
    flow = json.loads(flow_match.group(1))
    assert len(questions["fields"]) == 6
    assert len(flow["screens"]) == 12
    assert flow["counts"]["stable_capture_screens"] == 12
    assert "https://" not in text and "http://" not in text
    assert "cyan" not in text.lower()


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js required for JavaScript syntax check")
def test_standalone_simulation_javascript_is_syntax_valid(tmp_path: Path) -> None:
    text = (ROOT / "simulation/T4_12_ECRANS_EXECUTABLE.html").read_text()
    scripts = re.findall(r"<script(?: [^>]*)?>(.*?)</script>", text, re.S)
    script = tmp_path / "simulation.js"
    script.write_text(scripts[-1])
    subprocess.run(["node", "--check", str(script)], check=True, capture_output=True, text=True)
