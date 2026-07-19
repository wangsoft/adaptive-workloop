# Model Deltas

Routing is brand-blind (P1). Model identity matters only as measured behavior. This file defines the policy; `model-deltas.json` is the machine-readable ledger.

## Scope limits (P3)

An overlay entry may:
- Add counter-instructions (≤3 lines each) correcting a *specific observed behavior* of a model+harness pair.

An overlay entry may never:
- Change routes, gates, permissions, or risk classification.
- Replace or fork a workflow ("model X uses this other loop" is forbidden by design).
- Assert a capability the probe or the episode record doesn't show.

If a delta seems to require more than three lines to fix, it isn't a delta — it's a skill gap. File a proposal instead (SKILL.md, Self-improvement protocol).

## Conservative Default Profile — unknown or unmeasured models (P2)

Applies whenever the self-reported model id matches no active ledger entry. This includes every brand-new model. A new name is never an error.

- Same four routes, same gates, same authority as any model.
- Route 1 (Direct) reserved for trivially reversible, single-concern edits.
- Route 2+: run the narrowest relevant check after *every* meaningful edit, not batched.
- Route 4: checkpoint `progress.md` at half the normal interval.
- Claim discipline actively restated: no assertion without transcript evidence.

The profile is a tighter *cadence*, not a smaller *authority* — authority never varies by model (P4).

## In-Episode Capability Adjustment

Earned only for the current episode through a clean verification streak, no drift findings, and accurate self-classification. It never creates a persistent model profile by itself.

- May take larger steps between verifications and ask fewer alignment questions.
- May enlarge the next bounded increment; route and gates do not change from a streak alone.
- Explicitly not earned: skipping the verifier on high-risk work, expanded permissions, unattended irreversible actions.

## Ledger entry schema

| Field | Meaning |
|---|---|
| `id` | stable slug |
| `model_pattern` | substring/glob matched against the self-reported model id |
| `harness_pattern` | host name pattern from the probe (`*` if harness-independent) |
| `observed` | the specific behavior, one sentence, falsifiable |
| `evidence` | ≥2 independent episode manifests **or** one eval-run diff; with dates and paths |
| `counter_instruction` | ≤3 lines the agent applies when the pattern matches |
| `status` | `active` or `retired` |
| `retest_by` | expiry date — models update silently; stale deltas lie |

## Entry lifecycle

```
episode close-out observation → proposal (with eval case) → measured (evidence bar met)
  → active → retest by expiry → renewed or retired
```

Both directions are legitimate: deltas may tighten (model skips checks → add cadence) or loosen (model reliably self-verifies → note it as evidence toward Strong-Capability treatment). Retire on retest pass, on expiry, or when the eval that motivated the entry stops showing a difference (P6).

## Active ledger

`model-deltas.json` ships with an empty `entries` array. Only measured deltas may enter it; do not seed it from reputation, benchmarks, or marketing. Package checks reject malformed or expired active entries.

## Example entry — format illustration only, NOT measured, never apply

```yaml
- id: example-000
  model_pattern: "example-model-*"
  harness_pattern: "*"
  observed: "Describes edits as tested without having executed the test command."
  evidence: "NONE — illustrative. Real entries cite ≥2 episode manifests or an eval-run diff, with dates."
  counter_instruction: |
    After every edit, run the narrowest relevant check before describing
    the change as complete.
  status: retired
  retest_by: n/a
```
