from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_EVALS = ROOT / "scripts" / "run-evals"
CHECK = ROOT / "scripts" / "check"


class RoutingContractTests(unittest.TestCase):
    def test_implicit_trigger_is_narrow_and_has_enough_near_misses(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1]
        description_match = re.search(
            r'^description:\s*"([^"]+)"', frontmatter, re.MULTILINE
        )
        self.assertIsNotNone(description_match)
        description = description_match.group(1)
        self.assertIn("multi-step engineering task", description)
        self.assertIn("Not for one-step edits", description)
        self.assertNotIn("start of any development task", description)

        trigger_suite = json.loads((ROOT / "evals" / "trigger-cases.json").read_text())
        by_id = {case["id"]: case for case in trigger_suite["cases"]}
        negatives = [
            case for case in trigger_suite["cases"] if not case["should_trigger"]
        ]
        self.assertFalse(by_id["t-001"]["should_trigger"])
        self.assertGreaterEqual(len(negatives), 8)

    def test_outer_loop_authority_and_multi_agent_cost_gate_are_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        routes = (ROOT / "references" / "routes.md").read_text(encoding="utf-8")
        combined = skill + "\n" + routes

        self.assertNotIn("apply the stricter rule", combined)
        self.assertIn("One orchestration owner", routes)
        self.assertIn("Workloop owns route", routes)
        self.assertIn("Cost gate", routes)
        self.assertIn("communication artifact", routes)

    def test_missing_specialists_use_host_native_fallbacks_without_installing_dependencies(
        self,
    ) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        routes = (ROOT / "references" / "routes.md").read_text(encoding="utf-8")
        standalone = json.loads(
            (ROOT / "evals" / "standalone-cases.json").read_text(encoding="utf-8")
        )

        self.assertIn(
            "Specialists are optional accelerators, never dependencies", skill
        )
        self.assertIn(
            "Do not install, fetch, or enable a missing Skill during task execution",
            skill,
        )
        self.assertIn("host-native fallback", routes)
        self.assertIn("durable serial", routes)

        expected_by_route = {
            case["expected"]["route"]: case["expected"] for case in standalone["cases"]
        }
        self.assertEqual(
            set(expected_by_route),
            {"direct", "verified", "reviewed", "distributed"},
        )
        self.assertEqual(expected_by_route["reviewed"]["terminal"], "needs_human")
        self.assertEqual(
            expected_by_route["distributed"]["degradation"],
            "durable-serial",
        )


class EvalRunnerTests(unittest.TestCase):
    def test_validates_all_public_eval_suites(self) -> None:
        result = subprocess.run(
            [str(RUN_EVALS), "--validate"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("trigger", result.stdout)
        self.assertIn("behavior", result.stdout)
        self.assertIn("regression", result.stdout)
        self.assertIn("standalone", result.stdout)
        self.assertIn("profile codex-standalone", result.stdout)

    def test_trigger_adapter_receives_no_expected_labels_and_writes_run_artifacts(
        self,
    ) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--case",
                    "t-013",
                    "--adapter",
                    str(adapter),
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((Path(tmp) / "summary.json").read_text())
            self.assertEqual(summary["passed"], 2)
            requests = list(Path(tmp).glob("cases/*/request.json"))
            self.assertEqual(len(requests), 2)
            for request_path in requests:
                request = json.loads(request_path.read_text())
                self.assertNotIn("expected", request)
                self.assertNotIn("should_trigger", request)

    def test_missing_adapter_is_recorded_as_a_clean_eval_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--adapter",
                    str(Path(tmp) / "missing-adapter"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["errors"], 1)

    def test_codex_standalone_conformance_covers_all_routes_without_label_leakage(
        self,
    ) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_standalone_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "standalone",
                    "--adapter",
                    str(adapter),
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((Path(tmp) / "summary.json").read_text())
            self.assertEqual(summary["passed"], 4)
            self.assertEqual(summary["host_profile"]["id"], "codex-standalone")
            self.assertRegex(
                summary["host_profile"]["digest"], r"^sha256:[0-9a-f]{64}$"
            )

            requests = sorted(Path(tmp).glob("cases/*/request.json"))
            self.assertEqual(len(requests), 4)
            for request_path in requests:
                request = json.loads(request_path.read_text())
                self.assertNotIn("expected", request)
                self.assertEqual(request["host_profile"]["id"], "codex-standalone")
                self.assertEqual(
                    request["host_profile"]["capabilities"]["installed_skills"],
                    [],
                )

    def test_codex_standalone_rejects_an_unavailable_specialist_call(self) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_external_skill_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "standalone",
                    "--case",
                    "s-001",
                    "--adapter",
                    str(adapter),
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            summary = json.loads((Path(tmp) / "summary.json").read_text())
            self.assertEqual(summary["failed"], 1)
            grading = json.loads(
                (Path(tmp) / "cases" / "case-001" / "grading.json").read_text()
            )
            self.assertEqual(grading["unavailable_skill_calls"], ["gstack"])


class PackageCheckTests(unittest.TestCase):
    def test_repository_check_command_passes(self) -> None:
        if os.environ.get("WORKLOOP_CHECK_INNER") == "1":
            self.skipTest("avoid recursive check invocation")
        result = subprocess.run(
            [str(CHECK)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("check: PASS", result.stdout)
        self.assertFalse(
            (ROOT / "scripts" / "__pycache__").exists(),
            "scripts/check must not mutate an installed Skill package",
        )


if __name__ == "__main__":
    unittest.main()
