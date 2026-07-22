# Examples

One replayable episode snapshot so you can inspect what adaptive-workloop
produces before running it. Lifecycle, grading, per-check evidence, and bound
digests were written by the actual scripts. The manifest keeps a relative
repository root and illustrative snapshot metadata; verification evidence is
not abbreviated.

## `verified-invoice-rounding/` — a Route 2 (Verified) episode

Task: *"Add rounding to invoice totals with a regression test."* Low blast
radius, a deterministic check exists → **Verified**. Its source fixture lives at
`examples/fixtures/invoice-rounding/`; the episode files show the resulting
contract, verification, and lifecycle state:

| File | What it shows |
|---|---|
| `manifest.json` | Frozen facts: model (`fixture-future-model`, self-reported), host, route, repo head, and content digests. Immutable after creation. |
| `goal.json` | Clear outcome, success criterion, scope, constraints, risk, and authority. |
| `plan.json` | Ready single-agent topology with criterion/check mapping, budget, rollback, and fallback. |
| `contract.md` | Human-readable outcome, scope, risk, and completion map. No executable commands live here. |
| `checks.json` | One focused standard-library regression command with non-empty output assertions. |
| `progress.md` | Durable state for checkpoint/resume. |
| `handoff.md` | Slice handoff template (unused at Route 2; populated at Route 4). |
| `events.jsonl` | Append-only lifecycle: `created → work.started → verification.passed → episode.closed`. The durable write-ahead record. |
| `state.json` | Cache of current status, reconciled from the event chain. |
| `evidence/grading.json` | The complete `workloop-grading/1` result bound by digest to the `verification.passed` event. |
| `learning-candidates.jsonl` | Empty by design: this fixture produced no generalizable learning candidate. |

The takeaway: a provider-neutral future-model fixture ran the ordinary Verified
route with no special-casing; `done` is backed by a non-empty green test run,
matching per-check evidence, a grading digest, and an append-only lifecycle event.

To replay without modifying the checked-in snapshot, copy the repository or the
example to a scratch checkout, then run:

```bash
scripts/verify-contract examples/verified-invoice-rounding
```

A Route 4 (Distributed) episode looks the same plus a populated `handoff.md` per
slice and more frequent `progress.md` checkpoints; see
`references/long-running.md`.

## Maintainers

`grading.json` embeds wall-clock timestamps, so regeneration is not byte-for-byte
reproducible. `goal.json`, `plan.json`, `contract.md`, `checks.json`, `progress.md`, and `handoff.md` are
the authored source of truth; the lifecycle-derived files
(`manifest.json`, `events.jsonl`, `state.json`, `learning-candidates.jsonl`, `evidence/`) are rebuilt by:

```bash
make regen-example
```

The target uses a confined temporary local episode, rebuilds a mutually
digest-consistent snapshot, validates it before replacement, and cleans up in a
`finally` path. `tests/` guards the same invariant in CI.
