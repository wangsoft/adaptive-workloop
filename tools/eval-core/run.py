#!/usr/bin/env python3
"""Core-value A/B harness: does the SAME model do better WITH adaptive-workloop?

For each case, the same task is given to the model twice — once with no skill
(`bare`) and once with the skill installed (`workloop`) — in a fresh copy of the
fixture. Success is the fixture's own check passing, graded deterministically.
Before grading, each case's canonical check files are restored from graded/ over
the workspace, so a run cannot pass by deleting or weakening the test.

This measures the one thing P6 demands and the governance suites do not: whether
the skill beats the bare model on real outcomes. It calls the same provider
adapters documented in evals/adapter-contract.md. With `--validate` it uses a
bundled oracle adapter (no model) to prove the plumbing end to end.

Usage:
  run.py --validate
  run.py --adapter python3 --adapter evals/adapters/codex-cli \\
         --model-profile codex-gpt-5.6-sol-high --trials 3 \\
         --pass-env CODEX_HOME --pass-env WORKLOOP_ADAPTER_MODEL \\
         --output /tmp/core-eval
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONDITIONS = ("bare", "workloop")


def skill_digest(skill_path: Path) -> str:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from workloop_core import skill_runtime_digest  # type: ignore

        return skill_runtime_digest(skill_path)
    except Exception:
        return "sha256:unavailable"


def wilson(passes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = passes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--adapter",
        action="append",
        default=[],
        help="adapter argv token (repeat); e.g. --adapter python3 --adapter evals/adapters/codex-cli",
    )
    ap.add_argument("--model-profile", default="unspecified")
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--skill", type=Path, default=ROOT)
    ap.add_argument("--cases", type=Path, default=HERE / "cases.json")
    ap.add_argument("--output", type=Path, default=HERE / "runs")
    ap.add_argument("--pass-env", action="append", default=[])
    ap.add_argument(
        "--timeout", type=int, default=1800, help="per adapter call, seconds"
    )
    ap.add_argument(
        "--validate",
        action="store_true",
        help="use the bundled oracle adapter (no model) to prove plumbing",
    )
    return ap.parse_args()


def adapter_env(pass_env: list[str]) -> dict[str, str]:
    keep = ("PATH", "HOME", "LANG", "TMPDIR")
    base = {k: os.environ[k] for k in keep if k in os.environ}
    base["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in pass_env:
        if name in os.environ:
            base[name] = os.environ[name]
    return base


def run_case_trial(adapter, request, env, timeout):
    proc = subprocess.run(
        adapter,
        input=json.dumps(request),
        text=True,
        capture_output=True,
        cwd=ROOT,
        env=env,
        timeout=timeout,
        check=False,
    )
    resp = {}
    if proc.stdout.strip():
        try:
            resp = json.loads(proc.stdout.splitlines()[-1])
        except json.JSONDecodeError:
            resp = {}
    return proc.returncode, resp


def grade(case, workspace: Path) -> bool:
    fixture_name = Path(case["fixture"]).name
    for name in case.get("canonical_files", []):
        canonical = HERE / "graded" / fixture_name / name
        if canonical.is_file():
            shutil.copy2(canonical, workspace / name)
    check = case["check"]
    check_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        check["argv"],
        cwd=workspace,
        text=True,
        capture_output=True,
        env=check_env,
        check=False,
    )
    return result.returncode == check.get("expected_exit", 0)


def main() -> int:
    args = parse_args()
    cases = json.loads(args.cases.read_text())["cases"]
    if args.validate:
        adapter = [sys.executable, str(HERE / "fake_adapter.py")]
        trials = 1
    else:
        if not args.adapter:
            print("run.py: --adapter is required (or use --validate)", file=sys.stderr)
            return 2
        adapter = args.adapter
        trials = max(1, args.trials)

    env = adapter_env(args.pass_env)
    skill_path = args.skill.resolve()
    digest = skill_digest(skill_path)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    results = {c["id"]: {cond: [] for cond in CONDITIONS} for c in cases}

    # Provider adapters own workspace construction. Materialize a temporary
    # fixture root in their canonical <root>/<case-id> layout, then let the
    # shared adapter contract copy each fixture into artifact_root/project.
    # This keeps --validate and real-provider runs on the same path.
    with tempfile.TemporaryDirectory(prefix="adaptive-workloop-core-fixtures-") as tmp:
        fixture_root = Path(tmp)
        for case in cases:
            fixture = HERE / case["fixture"]
            shutil.copytree(fixture, fixture_root / case["id"])

        provider_env = {**env, "WORKLOOP_FIXTURE_ROOT": str(fixture_root)}
        for case in cases:
            for cond in CONDITIONS:
                for trial in range(1, trials + 1):
                    artifact_root = out / cond / case["id"] / f"trial-{trial}"
                    if artifact_root.exists():
                        shutil.rmtree(artifact_root, ignore_errors=True)
                    artifact_root.mkdir(parents=True)
                    workspace = artifact_root / "project"
                    request = {
                        "schema": "workloop-adapter-request/1",
                        "suite": "core",
                        "case_id": case["id"],
                        "trial": trial,
                        # The public adapter contract calls an installed skill
                        # "candidate"; the report's reader-facing condition is
                        # still "workloop".
                        "condition": "bare" if cond == "bare" else "candidate",
                        "model_profile": args.model_profile,
                        "prompt": case["prompt"],
                        "setup": {},
                        "artifact_root": str(artifact_root),
                        "skill": None
                        if cond == "bare"
                        else {
                            "name": "adaptive-workloop",
                            "path": str(skill_path),
                            "digest": digest,
                        },
                    }
                    started = time.time()
                    try:
                        rc, resp = run_case_trial(
                            adapter, request, provider_env, args.timeout
                        )
                        error = None if rc == 0 else f"adapter exit {rc}"
                    except subprocess.TimeoutExpired:
                        resp, error = {}, "timeout"
                    solved = False
                    if error is None:
                        try:
                            solved = grade(case, workspace)
                        except Exception as exc:  # noqa: BLE001
                            error = f"grade error: {exc}"
                    results[case["id"]][cond].append(
                        {
                            "trial": trial,
                            "solved": solved,
                            "error": error,
                            "seconds": round(time.time() - started, 2),
                            "usage": resp.get("usage", {}),
                        }
                    )

    report = summarize(cases, results, args, digest, trials)
    (out / "core-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print_summary(report, out)
    return 0


def summarize(cases, results, args, digest, trials):
    totals = {cond: {"passed": 0, "n": 0} for cond in CONDITIONS}
    per_case = []
    discordant_workloop_wins = 0
    discordant_bare_wins = 0
    for case in cases:
        row = {"id": case["id"], "risk": case.get("risk"), "conditions": {}}
        for cond in CONDITIONS:
            trials_list = results[case["id"]][cond]
            passed = sum(1 for t in trials_list if t["solved"])
            totals[cond]["passed"] += passed
            totals[cond]["n"] += len(trials_list)
            row["conditions"][cond] = {
                "passed": passed,
                "n": len(trials_list),
                "errors": [t["error"] for t in trials_list if t["error"]],
            }
        # paired discordance per trial index
        for i in range(trials):
            b = results[case["id"]]["bare"][i]["solved"]
            w = results[case["id"]]["workloop"][i]["solved"]
            if w and not b:
                discordant_workloop_wins += 1
            elif b and not w:
                discordant_bare_wins += 1
        per_case.append(row)

    rates = {}
    for cond in CONDITIONS:
        n = totals[cond]["n"]
        p = totals[cond]["passed"] / n if n else 0.0
        lo, hi = wilson(totals[cond]["passed"], n)
        rates[cond] = {
            "pass_rate": round(p, 4),
            "passed": totals[cond]["passed"],
            "n": n,
            "wilson95": [round(lo, 4), round(hi, 4)],
        }

    discordant = discordant_workloop_wins + discordant_bare_wins
    if discordant:
        win_lo, win_hi = wilson(discordant_workloop_wins, discordant)
    else:
        win_lo, win_hi = (0.0, 0.0)
    return {
        "schema": "workloop-core-result/1",
        "note": "Core-value A/B. Success = fixture check passes after the agent works, "
        "canonical test restored before grading. Not a promotion gate.",
        "validate_mode": args.validate,
        "model_profile": args.model_profile,
        "trials_per_case": trials,
        "skill_digest": digest,
        "conditions": rates,
        "delta_pass_rate": round(
            rates["workloop"]["pass_rate"] - rates["bare"]["pass_rate"], 4
        ),
        "paired": {
            "workloop_only_solved": discordant_workloop_wins,
            "bare_only_solved": discordant_bare_wins,
            "net_workloop_wins": discordant_workloop_wins - discordant_bare_wins,
            "workloop_win_rate_among_discordant_wilson95": [
                round(win_lo, 4),
                round(win_hi, 4),
            ],
        },
        "per_case": per_case,
    }


def print_summary(report, out: Path) -> None:
    c = report["conditions"]
    print(
        f"\ncore-value eval  (validate={report['validate_mode']}, "
        f"trials/case={report['trials_per_case']}, model={report['model_profile']})"
    )
    print(
        f"  bare      : {c['bare']['passed']}/{c['bare']['n']} "
        f"pass_rate={c['bare']['pass_rate']} wilson95={c['bare']['wilson95']}"
    )
    print(
        f"  workloop  : {c['workloop']['passed']}/{c['workloop']['n']} "
        f"pass_rate={c['workloop']['pass_rate']} wilson95={c['workloop']['wilson95']}"
    )
    print(f"  delta     : {report['delta_pass_rate']:+.4f} pass-rate")
    p = report["paired"]
    print(
        f"  paired    : workloop-only={p['workloop_only_solved']} "
        f"bare-only={p['bare_only_solved']} net={p['net_workloop_wins']:+d}"
    )
    if report["validate_mode"]:
        print(
            "  (validate: oracle solved both conditions — plumbing OK, delta must be 0)"
        )
    print(f"  result    : {out / 'core-result.json'}\n")


if __name__ == "__main__":
    raise SystemExit(main())
