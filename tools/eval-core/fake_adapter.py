#!/usr/bin/env python3
"""Oracle adapter for `run.py --validate` only.

It implements the `workloop-adapter-request/1` stdin/stdout contract like a real
provider adapter, but instead of calling a model it copies the reference
solution into the workspace. It solves every case IDENTICALLY for `bare` and
`workloop`, so a validation run proves the harness plumbing end to end
(fixture copy -> adapter -> canonical-test restore -> outcome grade -> paired
comparison) while producing ZERO spurious uplift. It is never used with real
models and makes no quality claim.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evals" / "adapters"))

from provider_common import prepare_workspace, read_request  # noqa: E402


def main() -> int:
    request = read_request()
    context = prepare_workspace(
        request, local_skill_path=Path(".agents/skills/adaptive-workloop")
    )
    case_id = request.get("case_id")

    cases = json.loads((HERE / "cases.json").read_text())
    case = next((c for c in cases["cases"] if c["id"] == case_id), None)
    if case is None:
        print(f"fake_adapter: unknown case {case_id}", file=sys.stderr)
        return 1

    fixture_name = Path(case["fixture"]).name
    solution_dir = HERE / "solutions" / fixture_name
    applied = []
    if solution_dir.is_dir():
        for src in sorted(solution_dir.glob("*.py")):
            shutil.copy2(src, context.workspace / src.name)
            applied.append(src.name)

    response = {
        "schema": "workloop-adapter-response/1",
        "activated": context.skill_installed,
        "route": "verified",
        "terminal": "complete",
        "degradation": None,
        "transcript": f"oracle applied: {applied}",
        "artifacts": [],
        "usage": {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        },
        "runtime": {
            "host": "fake-oracle",
            "configured_model": "oracle",
            "observed_model": "oracle",
            "effort": "none",
            "skill_installed": context.skill_installed,
        },
        "trace": {
            "skill_calls": ["adaptive-workloop"] if context.skill_installed else []
        },
    }
    sys.stdout.write(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
