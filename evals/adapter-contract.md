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
  "artifact_root": "/runner-owned/output/cases/case-001/workspace",
  "skill": {
    "name": "adaptive-workloop",
    "path": "/path/to/skill",
    "digest": "sha256:..."
  }
}
```

For `bare`, `skill` is `null`. For `previous`, `scripts/run-evals` requires `--previous-skill` and binds that exact checkout path and runtime-surface digest. Keep repository fixture, runtime envelope, tool catalog, sampling configuration, and independent grader equal across paired conditions.

`host_profile` is optional for the general suites and mandatory for standalone conformance. Its digest binds the exact capability envelope to the run. `installed_skills` lists optional Skills available in addition to the candidate under test. During an adapter execution, the runner creates `artifact_root` inside that case's output directory. Dry-run requests omit it.

## Response

```json
{
  "schema": "workloop-adapter-response/1",
  "activated": true,
  "route": "distributed",
  "terminal": "complete",
  "degradation": "durable-serial",
  "transcript": "raw agent transcript or artifact pointer",
  "artifacts": [{
    "path": ".workloop/tracked/example/state.json",
    "sha256": "sha256:..."
  }],
  "usage": {
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": null
  },
  "runtime": {
    "host": "codex",
    "configured_model": "gpt-5.6-sol",
    "observed_model": "gpt-5.6-sol",
    "effort": "high",
    "provider_command_digest": "sha256:...",
    "skill_installed": true
  },
  "trace": {
    "skill_calls": ["adaptive-workloop"]
  }
}
```

Trigger cases are graded exactly by the runner. Behavior and regression outputs remain `review_required` until an independent grader evaluates their transcript, state, artifacts, and trace. Do not let the producing adapter grade itself.

Standalone cases are also code-graded. The adapter must derive `trace.skill_calls` from host instrumentation rather than model prose. Any Skill other than `adaptive-workloop` fails the Codex-standalone profile; required artifacts, terminal state, route, and explicit degradation mode must also match. Every returned artifact path must be relative to `artifact_root`, resolve inside it, name a regular file, and match the declared SHA-256. Strings, missing files, symlink escapes, duplicate paths, and digest mismatches fail grading.

Exit status 0 means all code-graded cases passed. Status 1 means a failure or adapter error, 2 means invalid invocation or suite data, and 3 means all produced outputs are valid but at least one still requires independent review. Use `--allow-review-required` only for an explicit collection stage that handles that pending review downstream.

## Run evidence and process boundary

Every executed run writes `run-manifest.json` with schema `workloop-eval-run/2`. Its canonical digest binds the adapter runtime (including the built-in provider adapter's shared module), Skill runtime surfaces, full suite file, selected case IDs, condition, trial count, model/host profile, time and output limits, and environment-variable names explicitly passed to the adapter. It records names, never values. `summary.json` binds the manifest, and each case binds its request, response, and grading files.

The runner passes only a small OS allowlist plus variables named with `--pass-env`. It caps combined stdout/stderr before decoding, applies one deadline while writing stdin and while the adapter executes, and kills the adapter process group on failure. An adapter must apply an equally explicit boundary before invoking a nested provider CLI; the bundled adapters do this.

`model_profile` is the configured matrix label. Adapters must separately record the configured and provider-observed model IDs when instrumentation exposes them. Never silently replace an observed ID with the configured label.

## Matrix protocol

Run the same case selection and trial count separately for `bare`, `previous`, and `candidate`, using distinct output directories. Use at least three trials for nondeterministic models. Compare verified success, pass^k, human intervention, latency distribution, cost per verified outcome, tool path, rollback, and incidents—not route prose alone.

Repository-visible cases are public regressions. Keep release-decision held-out tasks outside the Skill repository and unavailable to the proposer.
