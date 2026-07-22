from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ANALYZE_TRACES = ROOT / "scripts" / "analyze-traces"
FIXTURE = ROOT / "evals" / "fixtures" / "trace-analysis" / "semantic-failures.jsonl"


class TraceAnalysisTests(unittest.TestCase):
    def test_runtime_contract_keeps_rlm_optional_and_governed(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "trace-evidence.md").read_text(
            encoding="utf-8"
        )
        contract = (ROOT / "evals" / "trace-analysis-contract.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cases = json.loads(
            (ROOT / "evals" / "trace-analysis-cases.json").read_text(encoding="utf-8")
        )

        self.assertIn("deterministic `scripts/analyze-traces` baseline first", skill)
        self.assertIn("Start with depth one", reference)
        self.assertIn("or authorizes promotion", reference)
        self.assertIn("Do not add a generic host REPL", reference)
        self.assertIn("HALO is not installed or required", readme)
        self.assertIn("promotion_authorized", contract)
        self.assertEqual(cases["evidence_class"], "public")
        self.assertEqual(len(cases["cases"]), 2)

    def run_analyzer(
        self, *extra: str
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name) / "report.json"
        result = subprocess.run(
            [
                str(ANALYZE_TRACES),
                "--trace",
                str(FIXTURE),
                "--output",
                str(output),
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        return result, output

    def validate_output(self, output: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(ANALYZE_TRACES),
                "--trace",
                str(FIXTURE),
                "--validate-report",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_baseline_binds_content_and_finds_semantic_failures(self) -> None:
        result, output = self.run_analyzer("--rlm-min-traces", "2")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["schema"], "workloop-trace-analysis/1")
        self.assertEqual(report["analysis"]["kind"], "deterministic_baseline")
        self.assertFalse(report["promotion_authorized"])
        self.assertEqual(report["dataset"]["trace_count"], 3)
        self.assertEqual(report["dataset"]["span_count"], 3)
        expected_file_digest = (
            "sha256:" + hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        )
        self.assertEqual(report["dataset"]["files"][0]["digest"], expected_file_digest)
        self.assertEqual(report["dataset"]["deployment_revisions"], ["abc123"])
        self.assertEqual(
            report["dataset"]["trace_observed_model_names"], ["provider/model-a"]
        )
        self.assertEqual(report["route"]["recommendation"], "bounded_rlm_candidate")
        self.assertEqual(report["route"]["maximum_depth"], 1)
        self.assertEqual(report["resource_usage"]["max_report_bytes"], 4 * 1024 * 1024)

        clusters = {cluster["category"]: cluster for cluster in report["clusters"]}
        self.assertEqual(clusters["timeout"]["trace_count"], 1)
        self.assertEqual(clusters["refusal"]["trace_count"], 1)
        self.assertEqual(clusters["incomplete"]["trace_count"], 2)
        self.assertEqual(clusters["otel_error"]["trace_count"], 1)
        self.assertIn("trace-ok", clusters["timeout"]["counterexample_trace_ids"])
        self.assertEqual(
            clusters["refusal"]["citations"][0],
            {
                "line": 3,
                "source_index": 0,
                "span_id": "span-refusal",
                "trace_id": "trace-refusal",
            },
        )
        self.assertNotIn("I cannot continue", json.dumps(report))
        self.assertEqual(
            report["digest"],
            self.canonical_digest(report, omit={"digest"}),
        )

    def test_small_dataset_stays_on_direct_baseline(self) -> None:
        result, output = self.run_analyzer()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["route"]["recommendation"], "direct_baseline")
        self.assertEqual(report["route"]["reasons"], [])

    def test_validate_report_rebinds_sources_and_citations(self) -> None:
        result, output = self.run_analyzer("--rlm-min-traces", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        validated = self.validate_output(output)

        self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
        self.assertIn("trace-analysis: VALID", validated.stdout)

        report = json.loads(output.read_text(encoding="utf-8"))
        report["clusters"][0]["citations"][0]["span_id"] = "fabricated"
        report["digest"] = self.canonical_digest(report, omit={"digest"})
        output.write_text(json.dumps(report), encoding="utf-8")
        rejected = self.validate_output(output)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("unknown trace/span citation", rejected.stderr)

    def test_validate_report_recomputes_route_and_deterministic_counts(self) -> None:
        result, output = self.run_analyzer("--rlm-min-traces", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))

        report["route"]["recommendation"] = "direct_baseline"
        report["route"]["reasons"] = []
        report["route"]["required_capabilities"] = []
        report["digest"] = self.canonical_digest(report, omit={"digest"})
        output.write_text(json.dumps(report), encoding="utf-8")
        rejected_route = self.validate_output(output)
        self.assertEqual(rejected_route.returncode, 2)
        self.assertIn("route does not match", rejected_route.stderr)

        subprocess.run(
            [
                str(ANALYZE_TRACES),
                "--trace",
                str(FIXTURE),
                "--output",
                str(output),
                "--rlm-min-traces",
                "2",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        report = json.loads(output.read_text(encoding="utf-8"))
        report["clusters"][0]["trace_count"] += 1
        report["clusters"][0]["prevalence"] = round(
            report["clusters"][0]["trace_count"] / report["dataset"]["trace_count"],
            6,
        )
        report["digest"] = self.canonical_digest(report, omit={"digest"})
        output.write_text(json.dumps(report), encoding="utf-8")
        rejected_count = self.validate_output(output)
        self.assertEqual(rejected_count.returncode, 2)
        self.assertIn("deterministic counts", rejected_count.stderr)

    def test_output_honors_report_size_limit(self) -> None:
        result, output = self.run_analyzer("--max-report-bytes", "128")

        self.assertEqual(result.returncode, 2)
        self.assertIn("report exceeds max report bytes", result.stderr)
        self.assertFalse(output.exists())

    def test_bounded_rlm_report_requires_safe_budgets_and_observed_identity(
        self,
    ) -> None:
        result, output = self.run_analyzer("--rlm-min-traces", "2")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        analysis = report["analysis"]
        analysis.update(
            {
                "kind": "bounded_rlm",
                "configured_model_identity": "configured/model-a",
                "observed_model_identity": "provider/model-a",
                "host_profile": "host/test",
                "budgets": {
                    "maximum_depth": 2,
                    "maximum_parallel_workers": 4,
                    "maximum_turns": 20,
                    "maximum_tokens": 10000,
                    "maximum_cost_usd": 5.0,
                    "maximum_duration_seconds": 120.0,
                },
                "usage": {
                    "turns": 5,
                    "tool_calls": 8,
                    "input_tokens": 2000,
                    "output_tokens": 1000,
                    "cost_usd": 1.0,
                    "duration_seconds": 30.0,
                },
            }
        )
        report["digest"] = self.canonical_digest(report, omit={"digest"})
        output.write_text(json.dumps(report), encoding="utf-8")

        rejected = self.validate_output(output)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("budgets are not safely bounded", rejected.stderr)

        analysis["budgets"]["maximum_depth"] = 1
        report["digest"] = self.canonical_digest(report, omit={"digest"})
        output.write_text(json.dumps(report), encoding="utf-8")
        validated = self.validate_output(output)
        self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)

    def test_report_with_sensitive_shaped_content_is_rejected(self) -> None:
        result, output = self.run_analyzer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        report["clusters"][0]["hypothesis"] = "api_key=abcdefghijk12345"
        report["clusters"][0]["confidence"] = "analyst_hypothesis"
        report["digest"] = self.canonical_digest(report, omit={"digest"})
        output.write_text(json.dumps(report), encoding="utf-8")

        rejected = self.validate_output(output)
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("sensitive-shaped content", rejected.stderr)

    def test_missing_stable_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = Path(temporary) / "invalid.jsonl"
            trace.write_text(
                '{"span_id":"span-only","status":{"code":"STATUS_CODE_OK"}}\n'
            )
            output = Path(temporary) / "report.json"
            result = subprocess.run(
                [
                    str(ANALYZE_TRACES),
                    "--trace",
                    str(trace),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("trace_id", result.stderr)
        self.assertFalse(output.exists())

    def test_baseline_rejects_sensitive_shaped_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            trace = Path(temporary) / "sensitive.jsonl"
            trace.write_text(
                '{"trace_id":"api_key=abcdefghijk12345","span_id":"span-1",'
                '"status":{"code":"STATUS_CODE_ERROR"}}\n'
            )
            output = Path(temporary) / "report.json"
            result = subprocess.run(
                [
                    str(ANALYZE_TRACES),
                    "--trace",
                    str(trace),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("sensitive-shaped content", result.stderr)
        self.assertFalse(output.exists())

    @staticmethod
    def canonical_digest(value: dict[str, object], *, omit: set[str]) -> str:
        reduced = {key: item for key, item in value.items() if key not in omit}
        encoded = json.dumps(
            reduced, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


if __name__ == "__main__":
    unittest.main()
