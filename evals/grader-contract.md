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
    {"criterion": "creates structured checks before editing", "status": "passed", "evidence": "transcript event 4"}
  ],
  "runtime": {
    "host": "claude-code",
    "configured_model": "claude-fable-5",
    "observed_model": "claude-fable-5"
  },
  "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": null}
}
```

Valid statuses are `passed`, `failed`, and `needs_human`. The runner requires `rationale` and a `criteria` array, but a release policy should additionally validate criterion-level evidence rather than trusting an aggregate verdict.

The grader runtime digest must differ from the producing adapter runtime digest. For meaningful independence, also use a fresh context and preferably a different provider/model family; always record the configured grader profile with `--grader-profile`. Digest inequality is a minimum mechanical guard, not proof of cognitive independence.

Exit status 0 means every review passed, 1 means a failed review or grader error, 2 means invalid or tampered source evidence, and 3 means at least one case still needs a human. `scripts/compare-evals` rejects pending/error runs and requires the grader configuration to match across conditions.
