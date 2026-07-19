from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_EVALS = ROOT / "scripts" / "run-evals"
GRADE_EVALS = ROOT / "scripts" / "grade-evals"
COMPARE_EVALS = ROOT / "scripts" / "compare-evals"
CODEX_ADAPTER = ROOT / "evals" / "adapters" / "codex-cli"
CLAUDE_ADAPTER = ROOT / "evals" / "adapters" / "claude-code"
CHECK = ROOT / "scripts" / "check"
sys.path.insert(0, str(ROOT / "scripts"))
from workloop_core import (  # noqa: E402
    BoundedCommandError,
    adapter_runtime_digest,
    run_bounded_command,
)


class BoundedCommandTests(unittest.TestCase):
    def test_timeout_applies_while_a_child_refuses_to_read_large_stdin(self) -> None:
        started = time.monotonic()
        with self.assertRaises(BoundedCommandError) as raised:
            run_bounded_command(
                [str(ROOT / "tests" / "fixtures" / "fake_no_stdin_adapter.py")],
                input_bytes=b"x" * (2 * 1024 * 1024),
                environment={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                timeout_seconds=0.1,
                max_output_bytes=4096,
            )
        self.assertEqual(raised.exception.kind, "timeout")
        self.assertLess(time.monotonic() - started, 1.0)


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

    def test_eval_run_manifest_binds_skill_adapter_dataset_and_case_artifacts(
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
                    "--adapter",
                    str(adapter),
                    "--model-profile",
                    "fixture-model",
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            run_dir = Path(tmp)
            manifest = json.loads((run_dir / "run-manifest.json").read_text())
            summary = json.loads((run_dir / "summary.json").read_text())
            request = json.loads(
                (run_dir / "cases" / "case-001" / "request.json").read_text()
            )

            self.assertEqual(manifest["schema"], "workloop-eval-run/2")
            self.assertEqual(manifest["model_profile"], "fixture-model")
            self.assertEqual(manifest["condition"], "candidate")
            self.assertRegex(manifest["adapter"]["digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertRegex(manifest["dataset"]["digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertRegex(manifest["skill"]["digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(manifest["dataset"]["case_ids"], ["t-001"])
            self.assertEqual(request["skill"]["digest"], manifest["skill"]["digest"])
            self.assertRegex(summary["run_manifest_digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(summary["run_manifest_digest"], manifest["digest"])
            self.assertRegex(summary["digest"], r"^sha256:[0-9a-f]{64}$")
            case_summary = summary["cases"][0]
            for field in ("request_digest", "response_digest", "grading_digest"):
                self.assertRegex(case_summary[field], r"^sha256:[0-9a-f]{64}$")

    def test_previous_condition_requires_and_binds_an_exact_skill_checkout(
        self,
    ) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            missing = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--condition",
                    "previous",
                    "--adapter",
                    str(adapter),
                    "--output",
                    str(Path(tmp) / "missing"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
            self.assertIn("--previous-skill", missing.stderr)

            run_dir = Path(tmp) / "bound"
            bound = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--condition",
                    "previous",
                    "--previous-skill",
                    str(ROOT),
                    "--adapter",
                    str(adapter),
                    "--output",
                    str(run_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(bound.returncode, 0, bound.stdout + bound.stderr)
            manifest = json.loads((run_dir / "run-manifest.json").read_text())
            request = json.loads(
                (run_dir / "cases" / "case-001" / "request.json").read_text()
            )
            self.assertEqual(manifest["skill"]["condition"], "previous")
            self.assertEqual(request["skill"]["digest"], manifest["skill"]["digest"])
            self.assertEqual(Path(request["skill"]["path"]), ROOT)

    def test_adapter_environment_is_deny_by_default_and_explicit_by_name(self) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_env_adapter.py"
        parent_env = os.environ.copy()
        parent_env["WORKLOOP_SECRET_CANARY"] = "must-not-cross-boundary"
        parent_env["SAFE_EVAL_FLAG"] = "explicit-value"
        with tempfile.TemporaryDirectory() as tmp:
            default_dir = Path(tmp) / "default"
            default_run = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--adapter",
                    str(adapter),
                    "--output",
                    str(default_dir),
                ],
                cwd=ROOT,
                env=parent_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                default_run.returncode, 0, default_run.stdout + default_run.stderr
            )
            default_response = json.loads(
                (default_dir / "cases" / "case-001" / "response.json").read_text()
            )
            self.assertFalse(default_response["runtime"]["secret_visible"])
            self.assertFalse(default_response["runtime"]["safe_flag_visible"])

            allowed_dir = Path(tmp) / "allowed"
            allowed_run = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--adapter",
                    str(adapter),
                    "--pass-env",
                    "SAFE_EVAL_FLAG",
                    "--output",
                    str(allowed_dir),
                ],
                cwd=ROOT,
                env=parent_env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                allowed_run.returncode, 0, allowed_run.stdout + allowed_run.stderr
            )
            allowed_response = json.loads(
                (allowed_dir / "cases" / "case-001" / "response.json").read_text()
            )
            manifest = json.loads((allowed_dir / "run-manifest.json").read_text())
            self.assertFalse(allowed_response["runtime"]["secret_visible"])
            self.assertTrue(allowed_response["runtime"]["safe_flag_visible"])
            self.assertEqual(
                manifest["runtime"]["passed_environment_names"], ["SAFE_EVAL_FLAG"]
            )

    def test_adapter_output_is_bounded_before_it_can_exhaust_runner_memory(
        self,
    ) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_large_output_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--adapter",
                    str(adapter),
                    "--max-output-bytes",
                    "4096",
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
            self.assertEqual(summary["errors"], 1)
            error = (Path(tmp) / "cases" / "case-001" / "error.txt").read_text()
            self.assertIn("output limit", error)
            manifest = json.loads((Path(tmp) / "run-manifest.json").read_text())
            self.assertEqual(manifest["runtime"]["max_output_bytes"], 4096)

    def test_adapter_timeout_terminates_the_entire_process_group(self) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_child_process_adapter.py"
        parent_env = os.environ.copy()
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "orphan-wrote-this"
            parent_env["CHILD_MARKER"] = str(marker)
            output = Path(tmp) / "run"
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--adapter",
                    str(adapter),
                    "--timeout",
                    "0.1",
                    "--pass-env",
                    "CHILD_MARKER",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=parent_env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            time.sleep(0.6)
            self.assertFalse(
                marker.exists(), "timed-out adapter left an orphan process"
            )
            error = (output / "cases" / "case-001" / "error.txt").read_text()
            self.assertIn("timed out", error)
            manifest = json.loads((output / "run-manifest.json").read_text())
            self.assertTrue(manifest["runtime"]["process_group_cleanup"])

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

    def test_review_required_is_not_reported_as_a_successful_eval(self) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "behavior",
                    "--case",
                    "bc-001",
                    "--adapter",
                    str(adapter),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["review_required"], 1)

    def test_review_required_can_be_explicitly_allowed_for_collection(self) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "behavior",
                    "--case",
                    "bc-001",
                    "--adapter",
                    str(adapter),
                    "--allow-review-required",
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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

    def test_codex_standalone_rejects_artifact_claims_without_verified_files(
        self,
    ) -> None:
        adapter = ROOT / "tests" / "fixtures" / "fake_claimed_artifact_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "standalone",
                    "--case",
                    "s-002",
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
            grading = json.loads(
                (Path(tmp) / "cases" / "case-001" / "grading.json").read_text()
            )
            self.assertIn("evidence/grading.json", grading["missing_artifacts"])
            self.assertTrue(grading["invalid_artifacts"])


class IndependentGraderTests(unittest.TestCase):
    def collect_behavior_run(self, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(RUN_EVALS),
                "--suite",
                "behavior",
                "--case",
                "bc-001",
                "--adapter",
                str(ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"),
                "--allow-review-required",
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_independent_grader_writes_bound_review_without_overwriting_source(
        self,
    ) -> None:
        grader = ROOT / "tests" / "fixtures" / "fake_grader.py"
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            collected = self.collect_behavior_run(run_dir)
            self.assertEqual(
                collected.returncode, 0, collected.stdout + collected.stderr
            )
            grading_path = run_dir / "cases" / "case-001" / "grading.json"
            source_grading = grading_path.read_bytes()

            result = subprocess.run(
                [str(GRADE_EVALS), "--run", str(run_dir), "--grader", str(grader)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(grading_path.read_bytes(), source_grading)
            review = json.loads((run_dir / "review-summary.json").read_text())
            manifest = json.loads((run_dir / "run-manifest.json").read_text())
            self.assertEqual(review["schema"], "workloop-review-summary/1")
            self.assertEqual(review["source_run_manifest_digest"], manifest["digest"])
            self.assertRegex(review["grader"]["digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(review["passed"], 1)
            review_case = review["cases"][0]
            for field in ("request_digest", "response_digest"):
                self.assertRegex(review_case[field], r"^sha256:[0-9a-f]{64}$")

    def test_grader_must_be_independent_from_the_producing_adapter(self) -> None:
        producer = ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            collected = self.collect_behavior_run(run_dir)
            self.assertEqual(
                collected.returncode, 0, collected.stdout + collected.stderr
            )

            result = subprocess.run(
                [str(GRADE_EVALS), "--run", str(run_dir), "--grader", str(producer)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("independent", result.stderr)
            self.assertFalse((run_dir / "review-summary.json").exists())

    def test_grader_rejects_tampered_source_artifacts(self) -> None:
        grader = ROOT / "tests" / "fixtures" / "fake_grader.py"
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            collected = self.collect_behavior_run(run_dir)
            self.assertEqual(
                collected.returncode, 0, collected.stdout + collected.stderr
            )
            response_path = run_dir / "cases" / "case-001" / "response.json"
            response_path.write_text("{}\n", encoding="utf-8")

            result = subprocess.run(
                [str(GRADE_EVALS), "--run", str(run_dir), "--grader", str(grader)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("digest mismatch", result.stderr)

    def test_grader_rejects_a_tampered_source_summary(self) -> None:
        grader = ROOT / "tests" / "fixtures" / "fake_grader.py"
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            collected = self.collect_behavior_run(run_dir)
            self.assertEqual(
                collected.returncode, 0, collected.stdout + collected.stderr
            )
            summary_path = run_dir / "summary.json"
            summary = json.loads(summary_path.read_text())
            summary["review_required"] = 0
            summary_path.write_text(json.dumps(summary) + "\n", encoding="utf-8")

            result = subprocess.run(
                [str(GRADE_EVALS), "--run", str(run_dir), "--grader", str(grader)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("summary digest mismatch", result.stderr)


class EvalComparisonTests(unittest.TestCase):
    def collect_trigger_run(
        self, output: Path, condition: str, model_profile: str = "fixture-model"
    ) -> subprocess.CompletedProcess[str]:
        command = [
            str(RUN_EVALS),
            "--suite",
            "trigger",
            "--case",
            "t-013",
            "--condition",
            condition,
            "--adapter",
            str(ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"),
            "--model-profile",
            model_profile,
            "--output",
            str(output),
        ]
        if condition == "previous":
            command.extend(["--previous-skill", str(ROOT)])
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_compare_reports_paired_delta_confidence_and_reliability_metrics(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bare_dir = Path(tmp) / "bare"
            previous_dir = Path(tmp) / "previous"
            candidate_dir = Path(tmp) / "candidate"
            self.collect_trigger_run(bare_dir, "bare")
            self.collect_trigger_run(previous_dir, "previous")
            self.collect_trigger_run(candidate_dir, "candidate")

            result = subprocess.run(
                [
                    str(COMPARE_EVALS),
                    "--bare",
                    str(bare_dir),
                    "--previous",
                    str(previous_dir),
                    "--candidate",
                    str(candidate_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["schema"], "workloop-eval-comparison/1")
            self.assertEqual(report["conditions"]["bare"]["pass_rate"], 0.0)
            self.assertEqual(report["conditions"]["candidate"]["pass_rate"], 1.0)
            self.assertEqual(report["deltas"]["candidate_vs_bare"]["pass_rate"], 1.0)
            self.assertEqual(
                report["deltas"]["candidate_vs_bare"]["paired_trials"][
                    "candidate_wins"
                ],
                1,
            )
            candidate = report["conditions"]["candidate"]
            self.assertEqual(candidate["per_case"]["t-013"]["pass_at_k"], 1.0)
            self.assertEqual(candidate["per_case"]["t-013"]["pass_pow_k"], 1.0)
            self.assertEqual(len(candidate["wilson_95"]), 2)

    def test_compare_rejects_incompatible_model_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bare_dir = Path(tmp) / "bare"
            candidate_dir = Path(tmp) / "candidate"
            self.collect_trigger_run(bare_dir, "bare", "baseline-model")
            self.collect_trigger_run(candidate_dir, "candidate", "candidate-model")

            result = subprocess.run(
                [
                    str(COMPARE_EVALS),
                    "--bare",
                    str(bare_dir),
                    "--candidate",
                    str(candidate_dir),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("model_profile", result.stderr)

    def test_compare_uses_bound_independent_reviews_for_behavior_runs(self) -> None:
        producer = ROOT / "tests" / "fixtures" / "fake_eval_adapter.py"
        grader = ROOT / "tests" / "fixtures" / "fake_grader.py"
        with tempfile.TemporaryDirectory() as tmp:
            run_dirs = {
                condition: Path(tmp) / condition for condition in ("bare", "candidate")
            }
            for condition, run_dir in run_dirs.items():
                collected = subprocess.run(
                    [
                        str(RUN_EVALS),
                        "--suite",
                        "behavior",
                        "--case",
                        "bc-001",
                        "--condition",
                        condition,
                        "--adapter",
                        str(producer),
                        "--model-profile",
                        "fixture-model",
                        "--allow-review-required",
                        "--output",
                        str(run_dir),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    collected.returncode, 0, collected.stdout + collected.stderr
                )
                reviewed = subprocess.run(
                    [
                        str(GRADE_EVALS),
                        "--run",
                        str(run_dir),
                        "--grader",
                        str(grader),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                expected_exit = 1 if condition == "bare" else 0
                self.assertEqual(
                    reviewed.returncode,
                    expected_exit,
                    reviewed.stdout + reviewed.stderr,
                )

            compared = subprocess.run(
                [
                    str(COMPARE_EVALS),
                    "--bare",
                    str(run_dirs["bare"]),
                    "--candidate",
                    str(run_dirs["candidate"]),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compared.returncode, 0, compared.stdout + compared.stderr)
            report = json.loads(compared.stdout)
            self.assertEqual(report["conditions"]["candidate"]["passed"], 1)
            self.assertEqual(report["conditions"]["bare"]["failed"], 1)


class ProviderAdapterTests(unittest.TestCase):
    def test_codex_cli_adapter_installs_only_candidate_and_derives_artifact_hashes(
        self,
    ) -> None:
        parent_env = os.environ.copy()
        parent_env["WORKLOOP_CODEX_BIN"] = str(
            ROOT / "tests" / "fixtures" / "fake_codex_cli.py"
        )
        parent_env["WORKLOOP_ADAPTER_MODEL"] = "gpt-fixture"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "standalone",
                    "--case",
                    "s-002",
                    "--adapter",
                    str(CODEX_ADAPTER),
                    "--model-profile",
                    "codex-gpt-fixture-high",
                    "--pass-env",
                    "WORKLOOP_CODEX_BIN",
                    "--pass-env",
                    "WORKLOOP_ADAPTER_MODEL",
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                env=parent_env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            response = json.loads(
                (Path(tmp) / "cases" / "case-001" / "response.json").read_text()
            )
            grading = json.loads(
                (Path(tmp) / "cases" / "case-001" / "grading.json").read_text()
            )
            manifest = json.loads((Path(tmp) / "run-manifest.json").read_text())
            self.assertEqual(
                manifest["adapter"]["digest"], adapter_runtime_digest(CODEX_ADAPTER)
            )
            self.assertEqual(response["runtime"]["host"], "codex")
            self.assertEqual(response["runtime"]["configured_model"], "gpt-fixture")
            self.assertEqual(
                response["runtime"]["observed_model"], "gpt-fixture-observed"
            )
            self.assertEqual(response["trace"]["skill_calls"], ["adaptive-workloop"])
            self.assertEqual(len(grading["verified_artifacts"]), 1)
            self.assertRegex(
                grading["verified_artifacts"][0]["sha256"],
                r"^sha256:[0-9a-f]{64}$",
            )

    def test_codex_cli_bare_condition_has_no_project_skill_or_skill_trace(self) -> None:
        parent_env = os.environ.copy()
        parent_env["WORKLOOP_CODEX_BIN"] = str(
            ROOT / "tests" / "fixtures" / "fake_codex_cli.py"
        )
        parent_env["WORKLOOP_ADAPTER_MODEL"] = "gpt-fixture"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "trigger",
                    "--case",
                    "t-001",
                    "--condition",
                    "bare",
                    "--adapter",
                    str(CODEX_ADAPTER),
                    "--model-profile",
                    "codex-gpt-fixture-high",
                    "--pass-env",
                    "WORKLOOP_CODEX_BIN",
                    "--pass-env",
                    "WORKLOOP_ADAPTER_MODEL",
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                env=parent_env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            response = json.loads(
                (Path(tmp) / "cases" / "case-001" / "response.json").read_text()
            )
            self.assertFalse(response["runtime"]["skill_installed"])
            self.assertEqual(response["trace"]["skill_calls"], [])

    def test_claude_code_adapter_uses_bare_isolation_and_instrumented_skill_trace(
        self,
    ) -> None:
        parent_env = os.environ.copy()
        parent_env["WORKLOOP_CLAUDE_BIN"] = str(
            ROOT / "tests" / "fixtures" / "fake_claude_cli.py"
        )
        parent_env["WORKLOOP_ADAPTER_MODEL"] = "claude-fable-fixture"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(RUN_EVALS),
                    "--suite",
                    "standalone",
                    "--case",
                    "s-003",
                    "--adapter",
                    str(CLAUDE_ADAPTER),
                    "--model-profile",
                    "claude-fable-fixture-high",
                    "--pass-env",
                    "WORKLOOP_CLAUDE_BIN",
                    "--pass-env",
                    "WORKLOOP_ADAPTER_MODEL",
                    "--output",
                    tmp,
                ],
                cwd=ROOT,
                env=parent_env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            response = json.loads(
                (Path(tmp) / "cases" / "case-001" / "response.json").read_text()
            )
            self.assertEqual(response["runtime"]["host"], "claude-code")
            self.assertEqual(
                response["runtime"]["configured_model"], "claude-fable-fixture"
            )
            self.assertEqual(response["trace"]["skill_calls"], ["adaptive-workloop"])
            self.assertEqual(response["terminal"], "needs_human")


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
