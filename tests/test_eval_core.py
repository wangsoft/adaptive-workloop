"""Guard the core-value A/B harness plumbing (no model, deterministic)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "tools" / "eval-core" / "run.py"


class EvalCoreHarnessTests(unittest.TestCase):
    def test_validate_proves_plumbing_with_zero_delta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(RUN), "--validate", "--output", tmp],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(tmp) / "core-result.json").read_text())

        # The oracle solves both conditions identically: plumbing works and the
        # comparison shows no spurious uplift.
        self.assertTrue(report["validate_mode"])
        self.assertEqual(report["delta_pass_rate"], 0.0)
        for condition in ("bare", "workloop"):
            data = report["conditions"][condition]
            self.assertGreaterEqual(data["n"], 5)
            self.assertEqual(data["passed"], data["n"])
        self.assertEqual(report["paired"]["net_workloop_wins"], 0)


if __name__ == "__main__":
    unittest.main()
