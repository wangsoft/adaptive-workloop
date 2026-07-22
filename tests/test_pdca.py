from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATE_EPISODE = ROOT / "scripts" / "create-episode"
EPISODE_STATE = ROOT / "scripts" / "episode-state"
VALIDATE_INTENT_PLAN = ROOT / "scripts" / "validate-intent-plan"
RECORD_LEARNING = ROOT / "scripts" / "record-learning"

PROFILE_DIMENSIONS = {
    "engineering": ["diff-scope", "runtime-or-artifact", "static-analysis", "tests"],
    "research": [
        "citation-traceability",
        "counterevidence",
        "freshness",
        "triangulation",
    ],
    "high_stakes": [
        "approvals",
        "authoritative-sources",
        "rollback",
        "specialist-review",
    ],
}


def create_episode(
    root: Path, *, route: str = "verified", profile: str = "engineering"
) -> Path:
    result = subprocess.run(
        [
            str(CREATE_EPISODE),
            "--task",
            "produce a bounded outcome",
            "--route",
            route,
            "--profile",
            profile,
            "--dir",
            str(root),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    storage = "tracked" if route == "distributed" else "local"
    return next((root / ".workloop" / storage).iterdir())


def write_ready_episode(
    episode: Path,
    *,
    route: str = "verified",
    profile: str = "engineering",
    overlap: bool = False,
) -> None:
    goal = {
        "schema": "workloop-goal/1",
        "status": "clear",
        "profile": profile,
        "outcome": "Produce a result whose acceptance is externally observable.",
        "success_criteria": [
            {"id": "outcome", "description": "The bounded result passes its check."}
        ],
        "scope": {
            "in": ["the bounded fixture"],
            "non_goals": ["external publication"],
        },
        "constraints": ["Keep all effects workspace-local."],
        "risks": [
            {
                "id": "false-green",
                "description": "A hollow check could pass.",
                "mitigation": "Require observable evidence.",
            }
        ],
        "unknowns": [],
        "authority": {
            "decision_owner": "user",
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
            "description": "Produce the bounded result.",
            "deliverable": "A locally verifiable artifact.",
            "owner_role": "builder",
            "depends_on": [],
            "goal_criteria": ["outcome"],
            "check_ids": ["truth"],
            "write_scope": ["src/"],
            "capabilities": ["workspace-write"],
            "effect": "workspace-local",
            "approval": {
                "required": False,
                "status": "not-required",
                "owner": "user",
            },
            "rollback": "Revert the bounded local change.",
            "parallel_group": "workers" if route == "distributed" else None,
        }
    ]
    if route == "distributed":
        steps.append(
            {
                **steps[0],
                "id": "document",
                "description": "Document the bounded result.",
                "deliverable": "A reviewable explanation.",
                "owner_role": "documenter",
                "goal_criteria": [],
                "write_scope": ["src/api/" if overlap else "docs/"],
            }
        )
    plan = {
        "schema": "workloop-plan/1",
        "status": "ready",
        "route": route,
        "topology": topology,
        "coordinator_role": "workloop-coordinator",
        "verification_owner_role": (
            "verifier" if route in {"reviewed", "distributed"} else "builder"
        ),
        "max_agent_depth": 1,
        "verification_dimensions": PROFILE_DIMENSIONS[profile],
        "steps": steps,
        "budget": {"wall_clock_minutes": 30, "retry_limit": 2},
        "stop_conditions": ["Stop after two failed full cycles."],
        "fallback": {
            "mode": "durable_serial",
            "trigger": "Use when independent workers are unavailable or the cost gate fails.",
        },
    }
    (episode / "goal.json").write_text(json.dumps(goal, indent=2) + "\n")
    (episode / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (episode / "checks.json").write_text(
        json.dumps(
            {
                "schema": "workloop-checks/1",
                "checks": [
                    {
                        "id": "truth",
                        "description": "Prove the bounded outcome.",
                        "argv": ["python3", "--version"],
                        "cwd": ".",
                        "risk": "workspace-local",
                    }
                ],
                "manual": [],
            },
            indent=2,
        )
        + "\n"
    )


class GoalPlanGateTests(unittest.TestCase):
    def test_create_episode_starts_v3_with_a_blocking_goal_and_draft_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp), profile="research")
            manifest = json.loads((episode / "manifest.json").read_text())
            goal = json.loads((episode / "goal.json").read_text())
            plan = json.loads((episode / "plan.json").read_text())

            self.assertEqual(manifest["schema"], "workloop-episode/3")
            self.assertEqual(goal["schema"], "workloop-goal/1")
            self.assertEqual(goal["status"], "needs_user")
            self.assertEqual(goal["profile"], "research")
            self.assertTrue(goal["unknowns"][0]["blocking"])
            self.assertEqual(plan["schema"], "workloop-plan/1")
            self.assertEqual(plan["status"], "draft")
            self.assertTrue((episode / "learning-candidates.jsonl").is_file())

    def test_work_cannot_start_until_goal_and_plan_are_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            result = subprocess.run(
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
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("readiness gate", result.stderr)
            self.assertEqual(
                json.loads((episode / "state.json").read_text())["status"], "open"
            )

    def test_ready_goal_plan_pass_and_cover_goal_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            write_ready_episode(episode)

            validated = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )
            started = subprocess.run(
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
                check=False,
            )

            self.assertEqual(
                validated.returncode, 0, validated.stdout + validated.stderr
            )
            self.assertIn("PASS", validated.stdout)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)

    def test_rejects_missing_goal_coverage_and_profile_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp), profile="research")
            write_ready_episode(episode, profile="research")
            plan = json.loads((episode / "plan.json").read_text())
            plan["steps"][0]["goal_criteria"] = []
            plan["verification_dimensions"] = ["freshness"]
            (episode / "plan.json").write_text(json.dumps(plan))

            result = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("uncovered goal criterion", result.stderr)
            self.assertIn("missing verification dimensions", result.stderr)

    def test_rejects_cyclic_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            write_ready_episode(episode)
            plan = json.loads((episode / "plan.json").read_text())
            plan["steps"].append(
                {
                    **plan["steps"][0],
                    "id": "second",
                    "goal_criteria": [],
                    "depends_on": ["deliver"],
                    "write_scope": ["docs/"],
                }
            )
            plan["steps"][0]["depends_on"] = ["second"]
            (episode / "plan.json").write_text(json.dumps(plan))

            result = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("dependency cycle", result.stderr)

    def test_rejects_overlapping_parallel_write_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp), route="distributed")
            write_ready_episode(episode, route="distributed", overlap=True)

            result = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("overlapping parallel write scopes", result.stderr)

    def test_high_stakes_profile_cannot_use_verified_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp), profile="high_stakes")
            write_ready_episode(episode, profile="high_stakes")

            result = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn(
                "high_stakes profile requires reviewed or distributed route",
                result.stderr,
            )

    def test_reviewed_route_requires_distinct_verification_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp), route="reviewed")
            write_ready_episode(episode, route="reviewed")
            plan = json.loads((episode / "plan.json").read_text())
            plan["verification_owner_role"] = "builder"
            (episode / "plan.json").write_text(json.dumps(plan))

            result = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("verification owner must be distinct", result.stderr)

    def test_step_effect_cannot_exceed_goal_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            write_ready_episode(episode)
            plan = json.loads((episode / "plan.json").read_text())
            step = plan["steps"][0]
            step["effect"] = "external"
            step["approval"] = {
                "required": True,
                "status": "pending",
                "owner": "user",
            }
            (episode / "plan.json").write_text(json.dumps(plan))

            result = subprocess.run(
                [str(VALIDATE_INTENT_PLAN), str(episode)],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("outside Goal authority", result.stderr)


class LearningCandidateTests(unittest.TestCase):
    def test_records_digest_bound_candidate_without_promoting_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            write_ready_episode(episode)
            result = subprocess.run(
                [
                    str(RECORD_LEARNING),
                    str(episode),
                    "--kind",
                    "memory",
                    "--claim",
                    "Goal coverage should be checked before execution.",
                    "--scope",
                    "adaptive-workloop",
                    "--evidence",
                    "goal.json",
                    "--writer",
                    "test-agent",
                    "--generalizability",
                    "project",
                    "--confidence",
                    "0.8",
                    "--dedupe-key",
                    "goal-coverage-before-work",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            event = json.loads((episode / "learning-candidates.jsonl").read_text())
            self.assertEqual(event["status"], "candidate")
            self.assertEqual(event["kind"], "memory")
            self.assertTrue(event["promotion"]["requires_explicit_approval"])
            self.assertTrue(event["promotion"]["requires_user_approval"])
            self.assertEqual(event["promotion"]["performed"], False)
            expected = (
                "sha256:"
                + hashlib.sha256((episode / "goal.json").read_bytes()).hexdigest()
            )
            self.assertEqual(event["evidence"][0]["digest"], expected)
            self.assertRegex(event["event_digest"], r"^sha256:[0-9a-f]{64}$")

    def test_refuses_secret_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            result = subprocess.run(
                [
                    str(RECORD_LEARNING),
                    str(episode),
                    "--kind",
                    "memory",
                    "--claim",
                    "Never persist this value.",
                    "--scope",
                    "user",
                    "--evidence",
                    "goal.json",
                    "--writer",
                    "test-agent",
                    "--generalizability",
                    "user",
                    "--confidence",
                    "0.5",
                    "--dedupe-key",
                    "secret-candidate",
                    "--sensitivity",
                    "secret",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual((episode / "learning-candidates.jsonl").read_text(), "")

    def test_refuses_duplicate_active_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            episode = create_episode(Path(tmp))
            argv = [
                str(RECORD_LEARNING),
                str(episode),
                "--kind",
                "project",
                "--claim",
                "Keep the same reusable claim.",
                "--scope",
                "adaptive-workloop",
                "--evidence",
                "goal.json",
                "--writer",
                "test-agent",
                "--generalizability",
                "project",
                "--confidence",
                "0.7",
                "--dedupe-key",
                "same-claim",
            ]
            first = subprocess.run(argv, text=True, capture_output=True, check=False)
            second = subprocess.run(argv, text=True, capture_output=True, check=False)

            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(second.returncode, 2, second.stdout + second.stderr)
            self.assertIn("active candidate already", second.stderr)
            self.assertEqual(
                len((episode / "learning-candidates.jsonl").read_text().splitlines()),
                1,
            )


if __name__ == "__main__":
    unittest.main()
