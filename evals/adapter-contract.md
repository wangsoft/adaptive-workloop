# Eval Adapter Contract

`scripts/run-evals` sends one JSON request on stdin and expects one JSON response on stdout. Adapter logs belong on stderr. The request deliberately omits expected labels and assertions.

## Request

```json
{
  "schema": "workloop-adapter-request/1",
  "suite": "trigger",
  "case_id": "t-013",
  "trial": 1,
  "condition": "candidate",
  "model_profile": "codex-gpt-5.6-sol-high",
  "host_profile": {
    "id": "codex-standalone",
    "digest": "sha256:...",
    "capabilities": {
      "schema": "workloop-capabilities/1",
      "subagents": false,
      "browser": false,
      "native_orchestration": "none",
      "installed_skills": []
    }
  },
  "prompt": "Resume the workloop episode from yesterday",
  "setup": {},
  "skill": {"name": "adaptive-workloop", "path": "/path/to/skill"}
}
```

For `bare`, `skill` is `null`. For `previous`, the adapter resolves the pinned previous Skill revision outside the request. Keep repository fixture, runtime envelope, tool catalog, and sampling configuration equal across paired conditions.

`host_profile` is optional for the general suites and mandatory for standalone conformance. Its digest binds the exact capability envelope to the run. `installed_skills` lists optional Skills available in addition to the candidate under test.

## Response

```json
{
  "schema": "workloop-adapter-response/1",
  "activated": true,
  "route": "distributed",
  "terminal": "complete",
  "degradation": "durable-serial",
  "transcript": "raw agent transcript or artifact pointer",
  "artifacts": ["workspace://..."],
  "usage": {
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": null
  },
  "runtime": {
    "host": "codex",
    "model": "gpt-5.6-sol",
    "effort": "high",
    "tool_manifest_digest": "sha256:..."
  },
  "trace": {
    "skill_calls": ["adaptive-workloop"]
  }
}
```

Trigger cases are graded exactly by the runner. Behavior and regression outputs remain `review_required` until an independent grader evaluates their transcript, state, artifacts, and trace. Do not let the producing adapter grade itself.

Standalone cases are also code-graded. The adapter must derive `trace.skill_calls` from host instrumentation rather than model prose. Any Skill other than `adaptive-workloop` fails the Codex-standalone profile; required artifacts, terminal state, route, and explicit degradation mode must also match.

## Matrix protocol

Run the same case selection and trial count separately for `bare`, `previous`, and `candidate`, using distinct output directories. Use at least three trials for nondeterministic models. Compare verified success, pass^k, human intervention, latency distribution, cost per verified outcome, tool path, rollback, and incidents—not route prose alone.

Repository-visible cases are public regressions. Keep release-decision held-out tasks outside the Skill repository and unavailable to the proposer.
