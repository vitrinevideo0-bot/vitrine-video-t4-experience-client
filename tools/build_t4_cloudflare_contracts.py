#!/usr/bin/env python3
"""Generate immutable TypeScript constants consumed by the T4 Worker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "config/T4_CAPTURE_FLOW_V1_0_0.json": ("cloudflare/src/capture_flow_contract.ts", "CAPTURE_FLOW_CONTRACT"),
    "form/questions_T4.json": ("cloudflare/src/form_contract.ts", "FORM_CONTRACT"),
    "config/T4_MUSIC_PACK_V1_0_0.json": ("cloudflare/src/music_pack_contract.ts", "MUSIC_PACK_CONTRACT"),
    "config/T4_VOICE_MIX_V1_0_0.json": ("cloudflare/src/voice_mix_contract.ts", "VOICE_MIX_CONTRACT"),
    "demo/render_job_complete_v1_0_0.json": ("cloudflare/src/render_job_template.ts", "RENDER_JOB_TEMPLATE"),
}


def generated_text(source: str, export_name: str) -> str:
    data = json.loads((ROOT / source).read_text(encoding="utf-8"))
    return f"// Generated from {source}; do not edit by hand.\nexport const {export_name} = " + json.dumps(data, ensure_ascii=False, indent=2) + " as const;\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail instead of rewriting when generated files diverge")
    args = parser.parse_args()
    stale: list[str] = []
    for source, (target, export_name) in CONTRACTS.items():
        output = ROOT / target
        expected = generated_text(source, export_name)
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != expected:
                stale.append(target)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(expected, encoding="utf-8")
            print(target)
    if stale:
        raise SystemExit("Stale Cloudflare contracts: " + ", ".join(stale))
    if args.check:
        print("T4_CLOUDFLARE_CONTRACTS_CURRENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
