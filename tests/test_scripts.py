from __future__ import annotations

import subprocess
import tempfile
import unittest
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_EPISODE = ROOT / "scripts" / "create-episode"
VERIFY_CONTRACT = ROOT / "scripts" / "verify-contract"
EPISODE_STATE = ROOT / "scripts" / "episode-state"
PROBE_CAPABILITIES = ROOT / "scripts" / "probe-capabilities"


class CreateEpisodeTests(unittest.TestCase):
    def test_rejects_slug_that_can_escape_episode_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "path safety",
                    "--route",
                    "verified",
                    "--slug",
                    "x/../../../escaped",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse((Path(tmp) / "escaped").exists())

    def test_rejects_multiline_task_before_rendering_templates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "safe title\n- [ ] injected :: test -d /tmp",
                    "--route",
                    "verified",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse((Path(tmp) / ".workloop").exists())

    def test_creates_a_bounded_local_episode_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "add safe validation",
                    "--route",
                    "verified",
                    "--model",
                    "test-model",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            episodes = list((Path(tmp) / ".workloop" / "local").glob("*"))
            self.assertEqual(len(episodes), 1)
            episode = episodes[0]
            manifest = json.loads((episode / "manifest.json").read_text())
            state = json.loads((episode / "state.json").read_text())
            checks = json.loads((episode / "checks.json").read_text())

            self.assertEqual(manifest["schema"], "workloop-episode/2")
            self.assertEqual(manifest["repo"]["root"], ".")
            self.assertEqual(manifest["storage"], "local")
            self.assertEqual(manifest["model"]["id"], "test-model")
            self.assertNotIn("status", manifest)
            self.assertRegex(manifest["skill"]["digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(state["status"], "open")
            self.assertEqual(checks["schema"], "workloop-checks/1")
            self.assertEqual(checks["checks"], [])
            self.assertEqual(checks["manual"], [])
            self.assertTrue((episode / "events.jsonl").is_file())
            self.assertIn(
                "local/", (Path(tmp) / ".workloop" / ".gitignore").read_text()
            )

    def test_migrates_legacy_ignore_all_state_for_distributed_durability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workloop = root / ".workloop"
            workloop.mkdir()
            (workloop / ".gitignore").write_text("*\n")

            result = subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "durable migration",
                    "--route",
                    "distributed",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            ignore = (workloop / ".gitignore").read_text()
            self.assertNotEqual(ignore.strip(), "*")
            self.assertIn("local/", ignore)
            self.assertTrue(any((workloop / "tracked").iterdir()))


class VerifyContractTests(unittest.TestCase):
    def test_rejects_freeform_shell_command_without_executing_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "must-not-exist"
            checks = root / "checks.json"
            checks.write_text(
                json.dumps(
                    {
                        "schema": "workloop-checks/1",
                        "checks": [
                            {
                                "id": "unsafe",
                                "description": "must be rejected",
                                "command": f"touch {marker}",
                            }
                        ],
                        "manual": [],
                    }
                )
            )

            result = subprocess.run(
                [str(VERIFY_CONTRACT), str(checks)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("argv", result.stdout + result.stderr)
            self.assertFalse(marker.exists())

    def test_closeout_is_strict_and_runs_from_repo_root_with_visible_output(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "strict closeout",
                    "--route",
                    "verified",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("Episode created:", created.stdout)
            episode = next((root / ".workloop" / "local").iterdir())
            (episode / "checks.json").write_text(
                json.dumps(
                    {
                        "schema": "workloop-checks/1",
                        "checks": [
                            {
                                "id": "repo-root",
                                "description": "runs at the repository root",
                                "argv": ["pwd"],
                                "cwd": ".",
                                "timeout_seconds": 5,
                                "expected_exit": 0,
                                "output_must_match": [re.escape(str(root))],
                                "risk": "workspace-local",
                            }
                        ],
                        "manual": [
                            {
                                "id": "human-look",
                                "description": "human confirms the result",
                                "status": "open",
                            }
                        ],
                    }
                )
            )

            result = subprocess.run(
                [str(VERIFY_CONTRACT), str(episode)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn(str(root), result.stdout)
            self.assertIn("manual criteria remain open", result.stdout)
            grading = json.loads((episode / "evidence" / "grading.json").read_text())
            self.assertFalse(grading["summary"]["passed"])

    def test_times_out_an_unbounded_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checks = root / "checks.json"
            checks.write_text(
                json.dumps(
                    {
                        "schema": "workloop-checks/1",
                        "checks": [
                            {
                                "id": "bounded",
                                "description": "command is bounded",
                                "argv": ["sleep", "1"],
                                "timeout_seconds": 0.05,
                                "risk": "workspace-local",
                            }
                        ],
                        "manual": [],
                    }
                )
            )

            started = __import__("time").monotonic()
            result = subprocess.run(
                [str(VERIFY_CONTRACT), str(checks)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            duration = __import__("time").monotonic() - started

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertLess(duration, 0.8)
            self.assertIn("TIMEOUT", result.stdout)

    def test_timeout_preserves_partial_output_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleeper = root / "partial-output-sleeper"
            sleeper.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "print('started-before-timeout', flush=True)\n"
                "time.sleep(2)\n"
            )
            sleeper.chmod(0o755)
            checks = root / "checks.json"
            checks.write_text(
                json.dumps(
                    {
                        "schema": "workloop-checks/1",
                        "checks": [
                            {
                                "id": "partial-output",
                                "description": "partial output is evidence",
                                "argv": [str(sleeper)],
                                "timeout_seconds": 0.8,
                                "risk": "workspace-local",
                            }
                        ],
                        "manual": [],
                    }
                )
            )

            result = subprocess.run(
                [str(VERIFY_CONTRACT), str(checks)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("TIMEOUT", result.stdout)
            self.assertIn("started-before-timeout", result.stdout)


class EpisodeStateTests(unittest.TestCase):
    def test_updates_mutable_state_and_appends_an_event_without_touching_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "distributed state",
                    "--route",
                    "distributed",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            episode = next((root / ".workloop" / "tracked").iterdir())
            manifest_before = (episode / "manifest.json").read_bytes()

            result = subprocess.run(
                [
                    str(EPISODE_STATE),
                    str(episode),
                    "--status",
                    "in_progress",
                    "--kind",
                    "work.started",
                    "--message",
                    "first bounded slice",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            state = json.loads((episode / "state.json").read_text())
            events = [
                json.loads(line)
                for line in (episode / "events.jsonl").read_text().splitlines()
            ]
            self.assertEqual(state["status"], "in_progress")
            self.assertEqual(state["last_event_seq"], 2)
            self.assertEqual(events[-1]["kind"], "work.started")
            self.assertEqual((episode / "manifest.json").read_bytes(), manifest_before)


class ProbeCapabilitiesTests(unittest.TestCase):
    def test_codex_standalone_profile_is_complete_and_probeable(self) -> None:
        profile_path = ROOT / "evals" / "profiles" / "codex-standalone.json"
        profile = json.loads(profile_path.read_text())

        self.assertEqual(profile["schema"], "workloop-capabilities/1")
        self.assertEqual(profile["profile_id"], "codex-standalone")
        self.assertEqual(profile["installed_skills"], [])
        self.assertFalse(profile["subagents"])
        self.assertFalse(profile["browser"])

        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    str(PROBE_CAPABILITIES),
                    tmp,
                    "--capabilities",
                    str(profile_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        probe = json.loads(result.stdout)
        self.assertEqual(probe["capabilities"]["self_report_required"], [])
        self.assertEqual(
            probe["capabilities"]["manifest"]["profile_id"],
            "codex-standalone",
        )

    def test_uses_complete_host_manifest_instead_of_truncated_directory_guessing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capability_path = root / "capabilities.json"
            installed = [f"skill-{index:03d}" for index in range(100)]
            capability_path.write_text(
                json.dumps(
                    {
                        "schema": "workloop-capabilities/1",
                        "subagents": True,
                        "browser": False,
                        "effort_mode": "high",
                        "permission_mode": "workspace-write",
                        "native_orchestration": "host",
                        "installed_skills": installed,
                    }
                )
            )

            result = subprocess.run(
                [
                    str(PROBE_CAPABILITIES),
                    str(root),
                    "--capabilities",
                    str(capability_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            probe = json.loads(result.stdout)
            self.assertEqual(probe["schema"], "workloop-probe/2")
            self.assertEqual(probe["capabilities"]["source"], "host-manifest")
            self.assertEqual(
                probe["capabilities"]["manifest"]["installed_skills"], installed
            )
            self.assertNotIn("truncated", probe["capabilities"])


if __name__ == "__main__":
    unittest.main()
