# Verification

Use the weakest check that can genuinely falsify the change. Route 2+ records executable criteria in `checks.json`; `contract.md` holds intent and scope only.

## Verification ladder

| Rung | Evidence | Typical failure caught |
|---|---|---|
| L0 | Diff readback against scope | typo, drift, accidental deletion |
| L1 | Format, lint, types | static interface misuse |
| L2 | Build or compile | integration breakage |
| L3 | Targeted tests | changed behavior |
| L4 | Integration or end-to-end tests | cross-boundary failure |
| L5 | Runtime/browser/CLI evidence | user-visible mismatch |
| L6 | Fresh-context verifier | builder blind spots and subjective quality |

## Structured check schema

Freeform shell strings are invalid. Use argv arrays so task text and Markdown cannot become executable instructions:

```json
{
  "schema": "workloop-checks/1",
  "checks": [
    {
      "id": "targeted-tests",
      "description": "invite validation regression passes",
      "argv": ["npm", "run", "test", "--", "invites"],
      "cwd": ".",
      "timeout_seconds": 120,
      "expected_exit": 0,
      "output_must_match": ["[1-9][0-9]* passing"],
      "risk": "workspace-local"
    }
  ],
  "manual": [
    {
      "id": "copy-review",
      "description": "error copy is clear and actionable",
      "status": "attested",
      "attested_by": "human-or-fresh-verifier",
      "evidence": "review/report.md#copy-review"
    }
  ]
}
```

Check IDs use lowercase letters, digits, and hyphens. `cwd` must remain inside the repository. Close-out is strict: empty criteria, schema errors, failed/timeout checks, missing output patterns, or open manual criteria fail.

## Execution boundary

`verify-contract`:

- Executes argv directly, never through a shell.
- Blocks shells, inline interpreter code, obvious destructive/network executables, and cwd escape.
- Enforces a per-check timeout and bounds captured output.
- Prints successful stdout/stderr and stores `evidence/check-<id>.json` plus `evidence/grading.json`.
- Requires `--allow-risk network` or `--allow-risk external-side-effect` for a declared non-local risk.

The verifier is not a sandbox. Package scripts and test runners can still execute repository code. Host permissions, isolation, network policy, and action-bound approval remain authoritative. Never hide push, publish, migration, deletion, payment, deploy, send, or other irreversible effects inside a verification check; invoke them directly through the host after approval.

## Evidence rules

- A claim counts only when this session ran the command and retained output or a referenced CI/runtime artifact.
- Re-read line numbers, dirty state, release state, and other source-of-truth facts in the current turn.
- Exit 0 alone is insufficient when the command can pass without exercising the changed path. Use `output_must_match`, a targeted test, coverage evidence, or a manual criterion.
- Pipelines that swallow failures, watch modes, interactive commands, and flaky checks cannot be the sole high-risk gate.

## Hollow greens

Treat as failure until disproved:

- zero tests collected, all relevant tests skipped, or filtered path not exercised;
- empty output satisfying weak assertions;
- setup failure occurring before assertions;
- a runtime smoke test for a recurring state/timing/visual bug with no pinned invariant;
- a self-review presented as independent verification.

For bug fixes, prefer a regression test that fails on the old behavior. When no honest seam exists, record the gap in the contract and use Reviewed; do not manufacture a decorative test.

## Cadence

Run narrow checks while editing and the full relevant contract at a boundary. A failing check may be rerun once to classify flakiness. Repeated full-cycle failure reroutes upward instead of creating an unbounded retry loop.
