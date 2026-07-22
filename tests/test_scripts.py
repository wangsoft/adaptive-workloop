from __future__ import annotations

import subprocess
import tempfile
import unittest
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_EPISODE = ROOT / "scripts" / "create-episode"
VERIFY_CONTRACT = ROOT / "scripts" / "verify-contract"
EPISODE_STATE = ROOT / "scripts" / "episode-state"
PROBE_CAPABILITIES = ROOT / "scripts" / "probe-capabilities"
CHECK_EPISODE = ROOT / "scripts" / "check-episode"
sys.path.insert(0, str(ROOT / "scripts"))
from workloop_core import skill_runtime_digest  # noqa: E402


def fill_goal_plan(episode: Path, *, check_id: str = "truth") -> None:
    manifest = json.loads((episode / "manifest.json").read_text())
    route = manifest["route"]
    goal = {
        "schema": "workloop-goal/1",
        "status": "clear",
        "profile": "engineering",
        "outcome": "Produce a locally verifiable result for the test fixture.",
        "success_criteria": [
            {"id": "outcome", "description": "The fixture result passes its check."}
        ],
        "scope": {"in": ["the bounded fixture"], "non_goals": ["external effects"]},
        "constraints": ["Keep the fixture deterministic and local."],
        "risks": [],
        "unknowns": [],
        "authority": {
            "decision_owner": "test-owner",
            "allowed_actions": ["workspace-local"],
            "approval_required": [],
        },
    }
    topology = {
        "verified": "single_agent",
        "reviewed": "producer_reviewer",
        "distributed": "coordinator_workers",
    }[route]
    steps = [
        {
            "id": "deliver",
            "description": "Produce the fixture result.",
            "deliverable": "A local fixture artifact.",
            "owner_role": "builder",
            "depends_on": [],
            "goal_criteria": ["outcome"],
            "check_ids": [check_id],
            "write_scope": ["fixture/"],
            "capabilities": ["workspace-write"],
            "effect": "workspace-local",
            "approval": {
                "required": False,
                "status": "not-required",
                "owner": "test-owner",
            },
            "rollback": "Delete the temporary fixture.",
        }
    ]
    if route == "distributed":
        steps.append(
            {
                **steps[0],
                "id": "document",
                "description": "Document the fixture result.",
                "deliverable": "A local fixture note.",
                "owner_role": "documenter",
                "goal_criteria": [],
                "write_scope": ["notes/"],
            }
        )
    plan = {
        "schema": "workloop-plan/1",
        "status": "ready",
        "route": route,
        "topology": topology,
        "coordinator_role": "coordinator",
        "verification_owner_role": "verifier" if route != "verified" else "builder",
        "max_agent_depth": 1,
        "verification_dimensions": [
            "diff-scope",
            "runtime-or-artifact",
            "static-analysis",
            "tests",
        ],
        "steps": steps,
        "budget": {"wall_clock_minutes": 5, "retry_limit": 1},
        "stop_conditions": ["Stop when the local check fails."],
        "fallback": {
            "mode": "durable_serial",
            "trigger": "Use when workers are unavailable.",
        },
    }
    (episode / "goal.json").write_text(json.dumps(goal, indent=2) + "\n")
    (episode / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")


def fill_episode_documents(episode: Path, *, check_id: str = "truth") -> None:
    fill_goal_plan(episode, check_id=check_id)
    (episode / "contract.md").write_text(
        """# Contract — test episode

## Outcome

Produce a locally verifiable result for the test fixture.

## Scope

- In: the bounded fixture
- Out / non-goals: external effects
- Owned paths: the temporary repository
- Interfaces that must remain compatible: workloop-checks/1

## Risk and trust boundaries

- Risk class: low
- Signals: none
- Untrusted inputs: none
- External or non-rerunnable effects: none
- Rollback boundary: delete the temporary directory
- What an independent verifier must attack: whether the command really runs

## Completion map

- Automatic check IDs: truth
- Manual attestation IDs: none

## Budgets and stop conditions

- Wall-clock / token / retry budget: one local attempt
- Stop and hand off when: the local command fails

## Decisions

- Keep the fixture deterministic and local.
""",
        encoding="utf-8",
    )
    (episode / "progress.md").write_text(
        """# Progress — test episode

## Verified state

- Phase: verification
- Verified true and evidence: checks.json defines the local command
- Assumed / unknown: none
- Broken: none
- Current state.json status: in_progress

## Completed units

- Contract prepared — checks.json — truth — evidence/grading.json

## Next actions

1. Run verify-contract and bind its grading artifact.

## Decisions and reroutes

- No reroute required.

## Blockers

- None.

## Not re-runnable

- None.

## Resume protocol

Read state.json, events.jsonl, progress.md, contract.md, and checks.json, then rerun verification.
""",
        encoding="utf-8",
    )
    (episode / "handoff.md").write_text(
        "# Handoff — test episode\n\nNot applicable to this non-distributed fixture.\n",
        encoding="utf-8",
    )


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

            self.assertEqual(manifest["schema"], "workloop-episode/3")
            self.assertEqual(manifest["repo"]["root"], ".")
            self.assertEqual(
                manifest["workspace"], {"kind": "artifact-root", "root": "."}
            )
            self.assertEqual(manifest["storage"], "local")
            self.assertEqual(manifest["model"]["id"], "test-model")
            self.assertNotIn("status", manifest)
            self.assertEqual(manifest["skill"]["digest"], skill_runtime_digest(ROOT))
            self.assertEqual(state["status"], "open")
            self.assertEqual(checks["schema"], "workloop-checks/1")
            self.assertEqual(checks["checks"], [])
            self.assertEqual(checks["manual"], [])
            self.assertEqual(
                json.loads((episode / "goal.json").read_text())["status"],
                "needs_user",
            )
            self.assertTrue((episode / "plan.json").is_file())
            self.assertTrue((episode / "learning-candidates.jsonl").is_file())
            self.assertTrue((episode / "events.jsonl").is_file())
            first_event = json.loads(
                (episode / "events.jsonl").read_text().splitlines()[0]
            )
            self.assertEqual(first_event["episode_id"], manifest["episode_id"])
            self.assertIsNone(first_event["from_status"])
            self.assertIn(
                "local/", (Path(tmp) / ".workloop" / ".gitignore").read_text()
            )
            self.assertIn(
                ".gitignore", (Path(tmp) / ".workloop" / ".gitignore").read_text()
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

    def test_local_runtime_ignore_keeps_a_git_worktree_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initialized = subprocess.run(
                ["git", "init", "-q"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                initialized.returncode, 0, initialized.stdout + initialized.stderr
            )

            created = subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "keep local state invisible",
                    "--route",
                    "verified",
                    "--dir",
                    str(root),
                    "--storage",
                    "local",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            status = subprocess.run(
                ["git", "status", "--porcelain=v1"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(status.stdout, "")


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
            fill_episode_documents(episode, check_id="repo-root")
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

    def test_rejects_a_zero_test_hollow_green_even_with_exit_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "empty-test-runner"
            runner.write_text(
                "#!/usr/bin/env python3\nprint('Ran 0 tests in 0.000s')\n",
                encoding="utf-8",
            )
            runner.chmod(0o755)
            checks = root / "checks.json"
            checks.write_text(
                json.dumps(
                    {
                        "schema": "workloop-checks/1",
                        "checks": [
                            {
                                "id": "tests",
                                "description": "targeted tests exercise the change",
                                "argv": [str(runner)],
                                "timeout_seconds": 5,
                                "risk": "workspace-local",
                            }
                        ],
                        "manual": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [str(VERIFY_CONTRACT), str(checks)],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("HOLLOW", result.stdout)
            grading = json.loads((root / "evidence" / "grading.json").read_text())
            self.assertFalse(grading["summary"]["passed"])

    def test_rejects_unfilled_episode_documents_before_running_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "reject placeholder contract",
                    "--route",
                    "verified",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            episode = next((root / ".workloop" / "local").iterdir())
            self.write_placeholder_check(episode)
            fill_goal_plan(episode)

            result = subprocess.run(
                [str(VERIFY_CONTRACT), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("unfilled placeholder", result.stderr)

    def write_placeholder_check(self, episode: Path) -> None:
        (episode / "checks.json").write_text(
            json.dumps(
                {
                    "schema": "workloop-checks/1",
                    "checks": [
                        {
                            "id": "truth",
                            "description": "would pass if the contract were complete",
                            "argv": ["pwd"],
                            "risk": "workspace-local",
                        }
                    ],
                    "manual": [],
                }
            ),
            encoding="utf-8",
        )

    def test_timeout_preserves_partial_output_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sleeper = root / "partial-output-sleeper"
            sleeper.write_text(
                "#!/usr/bin/env python3\n"
                "import time\n"
                "print('started-before-timeout', flush=True)\n"
                "time.sleep(5)\n"
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
                                "timeout_seconds": 2,
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
    def write_passing_checks(self, episode: Path) -> None:
        (episode / "checks.json").write_text(
            json.dumps(
                {
                    "schema": "workloop-checks/1",
                    "checks": [
                        {
                            "id": "truth",
                            "description": "a real local command passes",
                            "argv": ["pwd"],
                            "cwd": ".",
                            "timeout_seconds": 5,
                            "expected_exit": 0,
                            "risk": "workspace-local",
                        }
                    ],
                    "manual": [],
                }
            ),
            encoding="utf-8",
        )

    def start_and_verify(self, episode: Path) -> None:
        fill_episode_documents(episode)
        self.write_passing_checks(episode)
        subprocess.run(
            [
                str(EPISODE_STATE),
                str(episode),
                "--status",
                "in_progress",
                "--kind",
                "work.started",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [str(VERIFY_CONTRACT), str(episode)],
            text=True,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [
                str(EPISODE_STATE),
                str(episode),
                "--status",
                "verified",
                "--kind",
                "verification.passed",
                "--evidence",
                "evidence/grading.json",
            ],
            text=True,
            capture_output=True,
            check=True,
        )

    def test_verified_requires_a_bound_passing_grading_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "reject hollow verification",
                    "--route",
                    "verified",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            episode = next((root / ".workloop" / "local").iterdir())
            fill_episode_documents(episode)
            self.write_passing_checks(episode)
            subprocess.run(
                [str(EPISODE_STATE), str(episode), "--status", "in_progress"],
                text=True,
                capture_output=True,
                check=True,
            )

            missing = subprocess.run(
                [str(EPISODE_STATE), str(episode), "--status", "verified"],
                text=True,
                capture_output=True,
                check=False,
            )
            (episode / "evidence" / "grading.json").write_text(
                json.dumps(
                    {"schema": "workloop-grading/1", "summary": {"passed": True}}
                ),
                encoding="utf-8",
            )
            forged = subprocess.run(
                [
                    str(EPISODE_STATE),
                    str(episode),
                    "--status",
                    "verified",
                    "--kind",
                    "verification.passed",
                    "--evidence",
                    "evidence/grading.json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
            self.assertIn("verification gate", missing.stderr)
            self.assertEqual(forged.returncode, 1, forged.stdout + forged.stderr)
            self.assertIn("checks digest", forged.stderr)
            state = json.loads((episode / "state.json").read_text())
            self.assertEqual(state["status"], "in_progress")

    def test_manifest_drift_is_rejected_before_any_state_transition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "bind immutable manifest",
                    "--route",
                    "verified",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            episode = next((root / ".workloop" / "local").iterdir())
            state_before = (episode / "state.json").read_bytes()
            manifest = json.loads((episode / "manifest.json").read_text())
            manifest["task"] = "tampered after creation"
            (episode / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            result = subprocess.run(
                [str(EPISODE_STATE), str(episode), "--status", "in_progress"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("manifest digest", result.stderr)
            self.assertEqual((episode / "state.json").read_bytes(), state_before)

    def test_verified_binds_grading_digest_and_complete_rejects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "bind verification evidence",
                    "--route",
                    "verified",
                    "--dir",
                    tmp,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            episode = next((root / ".workloop" / "local").iterdir())
            self.start_and_verify(episode)
            events = [
                json.loads(line)
                for line in (episode / "events.jsonl").read_text().splitlines()
            ]
            grading_digest = events[-1]["evidence_digests"]["evidence/grading.json"]
            self.assertRegex(grading_digest, r"^sha256:[0-9a-f]{64}$")

            grading = json.loads((episode / "evidence" / "grading.json").read_text())
            grading["summary"]["auto_pass"] = 99
            (episode / "evidence" / "grading.json").write_text(
                json.dumps(grading), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    str(EPISODE_STATE),
                    str(episode),
                    "--status",
                    "complete",
                    "--kind",
                    "episode.closed",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                completed.returncode, 1, completed.stdout + completed.stderr
            )
            self.assertIn("changed after verification", completed.stderr)
            state = json.loads((episode / "state.json").read_text())
            self.assertEqual(state["status"], "verified")

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
            fill_episode_documents(episode)
            self.write_passing_checks(episode)

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

    def test_recovers_state_from_the_append_only_event_log_before_transitioning(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "recover durable state",
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
            fill_episode_documents(episode)
            self.write_passing_checks(episode)
            subprocess.run(
                [str(EPISODE_STATE), str(episode), "--status", "in_progress"],
                text=True,
                capture_output=True,
                check=True,
            )
            manifest = json.loads((episode / "manifest.json").read_text())
            pending_event = {
                "schema": "workloop-event/1",
                "seq": 3,
                "at": "2026-07-19T00:00:00Z",
                "episode_id": manifest["episode_id"],
                "kind": "worker.blocked",
                "from_status": "in_progress",
                "status": "blocked",
                "message": "simulated crash after durable event append",
                "evidence": [],
            }
            with (episode / "events.jsonl").open("a", encoding="utf-8") as events:
                events.write(json.dumps(pending_event, sort_keys=True) + "\n")

            result = subprocess.run(
                [
                    str(EPISODE_STATE),
                    str(episode),
                    "--status",
                    "in_progress",
                    "--kind",
                    "work.resumed",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("blocked -> in_progress", result.stdout)
            state = json.loads((episode / "state.json").read_text())
            events = [
                json.loads(line)
                for line in (episode / "events.jsonl").read_text().splitlines()
            ]
            self.assertEqual(state["last_event_seq"], 4)
            self.assertEqual(state["status"], "in_progress")
            self.assertEqual([event["seq"] for event in events], [1, 2, 3, 4])

    def test_tracked_episode_must_pass_redaction_gate_before_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "protect handoff evidence",
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
            self.start_and_verify(episode)
            canary = "sk-" + "A" * 40
            (episode / "handoff.md").write_text(
                f"# Handoff\n\napi_key: {canary}\n", encoding="utf-8"
            )

            scan = subprocess.run(
                [str(CHECK_EPISODE), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )
            blocked = subprocess.run(
                [
                    str(EPISODE_STATE),
                    str(episode),
                    "--status",
                    "complete",
                    "--kind",
                    "episode.closed",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(scan.returncode, 1, scan.stdout + scan.stderr)
            self.assertNotIn(canary, scan.stdout + scan.stderr)
            self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
            state = json.loads((episode / "state.json").read_text())
            self.assertEqual(state["status"], "verified")

            (episode / "handoff.md").write_text(
                "# Handoff\n\napi_key: [REDACTED]\n", encoding="utf-8"
            )
            clean = subprocess.run(
                [str(CHECK_EPISODE), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )
            completed = subprocess.run(
                [
                    str(EPISODE_STATE),
                    str(episode),
                    "--status",
                    "complete",
                    "--kind",
                    "episode.closed",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )

    def test_refuses_a_non_contiguous_event_log_without_mutating_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(
                [
                    str(CREATE_EPISODE),
                    "--task",
                    "reject corrupt journal",
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
            state_before = (episode / "state.json").read_bytes()
            corrupt = {
                "schema": "workloop-event/1",
                "seq": 3,
                "at": "2026-07-19T00:00:00Z",
                "kind": "sequence.skipped",
                "from_status": "open",
                "status": "in_progress",
            }
            with (episode / "events.jsonl").open("a", encoding="utf-8") as events:
                events.write(json.dumps(corrupt, sort_keys=True) + "\n")

            result = subprocess.run(
                [str(EPISODE_STATE), str(episode), "--status", "in_progress"],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("non-contiguous sequence", result.stderr)
            self.assertEqual((episode / "state.json").read_bytes(), state_before)


class ProbeCapabilitiesTests(unittest.TestCase):
    def test_repository_digest_changes_when_dirty_file_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "workloop@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Workloop Test"],
                cwd=root,
                check=True,
            )
            tracked = root / "tracked.txt"
            tracked.write_text("baseline\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "baseline"], cwd=root, check=True
            )

            tracked.write_text("dirty version one\n", encoding="utf-8")
            first = subprocess.run(
                [str(PROBE_CAPABILITIES), str(root)],
                text=True,
                capture_output=True,
                check=True,
            )
            tracked.write_text("dirty version two\n", encoding="utf-8")
            second = subprocess.run(
                [str(PROBE_CAPABILITIES), str(root)],
                text=True,
                capture_output=True,
                check=True,
            )

            first_git = json.loads(first.stdout)["git"]
            second_git = json.loads(second.stdout)["git"]
            self.assertEqual(first_git["dirty_files"], second_git["dirty_files"])
            self.assertNotEqual(first_git["state_digest"], second_git["state_digest"])
            self.assertEqual(first_git["snapshot_schema"], "workloop-repo-snapshot/1")

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
