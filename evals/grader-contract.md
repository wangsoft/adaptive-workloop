# Independent Grader Contract

`scripts/grade-evals` accepts only completed `behavior` or `regression` collections whose cases remain `review_required`. It verifies the source manifest, dataset, request, response, and original grading digests before invoking a grader. Review output is written under `reviews/` plus `review-summary.json`; source `grading.json` files are never overwritten.

The grader executable receives one JSON request on stdin:

```json
{
  "schema": "workloop-grader-request/1",
  "source": {
    "run_manifest_digest": "sha256:...",
    "suite": "behavior",
    "condition": "candidate",
    "model_profile": "codex-gpt-5.6-sol-high",
    "artifact_id": "case-001",
    "case_id": "bc-001",
    "trial": 1,
    "request_digest": "sha256:...",
    "response_digest": "sha256:...",
    "grading_digest": "sha256:..."
  },
  "expected": {"route": "verified", "must": [], "must_not": []},
  "criteria": [
    {"id": "route", "kind": "route", "expectation": "route equals verified"},
    {"id": "must-001", "kind": "must", "expectation": "creates structured checks before editing"}
  ],
  "producer_request": {},
  "producer_response": {},
  "producer_grading": {"status": "review_required"}
}
```

It returns exactly one JSON object on stdout; logs belong on stderr:

```json
{
  "schema": "workloop-grader-response/1",
  "status": "passed",
  "rationale": "Every must criterion is evidenced and no must_not is present.",
  "criteria": [
    {"criterion_id": "must-001", "criterion": "creates structured checks before editing", "status": "passed", "evidence": "transcript event 4"}
  ],
  "runtime": {
    "host": "claude-code",
    "configured_model": "claude-fable-5",
    "observed_model": "claude-fable-5"
  },
  "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": null}
}
```

Valid statuses are `passed`, `failed`, and `needs_human`. The response must contain exactly one unique record for every bound criterion ID and must echo its expectation exactly. The runner rejects missing, duplicate, substituted, or extra criteria, and derives the only valid aggregate status from the criterion statuses. This proves structural coverage, not that free-text evidence is truthful; judge calibration and human release review remain necessary.

The grader runtime digest must differ from the producing adapter runtime digest. Promotion v2 additionally requires complete, stable provider-observed model identities across the selected comparisons, one frozen grader binding, and no overlap between producer and grader observed model IDs. A missing observed identity is inconclusive; identity drift or overlap fails the gate. For meaningful independence, also use a fresh context and preferably a different provider/model family; always record the configured grader profile with `--grader-profile`. Executable-digest and identity inequality are minimum mechanical guards, not proof of cognitive independence or grader calibration.

Bundled `codex-grader` and `claude-grader` adapters enforce fresh temporary workspaces and structured output. Codex runs read-only with user config and project rules ignored. Claude disables tools, slash commands, session persistence, and non-explicit MCP. Both keep configured and provider-observed identities separate. The producer transcript remains untrusted input even though it is included for evidence review.

For an external dataset, `grade-evals` requires the exact `--dataset` path again. Its file digest, `evidence_class`, origin, and `held_out` boolean must match the producing run. A repository run cannot be relabeled or graded against an alternate file.

Exit status 0 means every review passed, 1 means a failed review or grader error, 2 means invalid or tampered source evidence, and 3 means at least one case still needs a human. `scripts/compare-evals` rejects pending/error runs and requires the grader configuration to match across conditions.
