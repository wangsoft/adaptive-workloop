# Improvement Protocol

How the Skill improves itself without being able to modify itself (P5, P6). Read this only during a dedicated improvement episode, never during ordinary task execution.

## During a task

Record observed routing or verification failures as they happen, but do not edit the installed Skill in that task. Improvement is a separate, human-run episode.

## Freeze a proposal

In a separate improvement episode, freeze a structured `workloop-improvement-proposal/2` before exposing any held-out result. The proposal must name one editable surface, one exact hook, one mechanism family, the failure signature and evidence, expected affected/protected cases, actual changed paths, search position, and trial/cost/time budgets. Validate it against the exact previous and candidate checkouts:

```bash
scripts/validate-proposal \
  --proposal .workloop/proposals/<proposal>.json \
  --registry evals/editable-surfaces.json \
  --previous-skill /path/to/previous \
  --candidate-skill /path/to/candidate \
  --output /private/evals/<proposal>-validation.json
```

`evals/editable-surfaces.json` allows at most one typed surface per proposal. Scripts, provider/grader adapters, host profiles, the surface registry, and the promotion policy are protected. Stable public case/control files participate in the Skill digest and actual-diff check, while generated eval outputs do not. The validation attestation binds the current validator, registry, proposal, exact Skill digests, actual diff, search counters, and budgets. It never authorizes promotion.

## Four evidence classes

Promotion requires four separately bound evidence classes:

1. `public`: all visible regressions remain green.
2. `held-in`: the failure-derived target set shows a minimum uplift and paired effect.
3. `held-out`: proposer-blind private evidence is evaluated once after proposal freeze.
4. `audit-held-out`: a separate one-shot final audit remains unseen until the candidate is otherwise frozen.

Run private classes through `scripts/run-sealed-matrix`; the dataset must be a mode-0600 regular file outside both the Skill checkout and output root. Initialize one `scripts/search-ledger` before candidate evaluation, append every comparison before closing that candidate as rejected or selected, and pass the closed ledger to `scripts/decide-promotion`. The bundled v2 policy bounds the complete recorded search—not only the selected candidate—across candidates, rounds, private exposure, trials, reported cost, and duration. It also requires stable provider-observed producer/grader identities, a distinct observed grader model, numeric token/cost ratios, and a Wilson lower bound over discordant paired trials. Keep rejected changes and negative runs as regression evidence. Never let the optimized Skill own the evaluator, ledger, dataset broker, permission boundary, or final release gate.

## Role separation

Eval evidence is immutable and role-separated. `scripts/run-evals` binds the exact Skill, adapter runtime, dataset evidence class, cases, host, model profile, and runtime envelope; the producing adapter cannot grade behavior or regression output. Prefer `scripts/run-matrix` to collect, independently grade, and compare bare/previous/candidate through an append-only resumable stage log. External datasets must explicitly and consistently declare `public`, `held-in`, `held-out`, or `audit-held-out`; expected labels never enter producer requests.

## Decision

Apply `scripts/decide-promotion` to the closed search ledger plus the public, held-in, held-out, and audit-held-out comparison artifacts. It fails closed on missing evidence, candidate/proposal drift, leakage counters, search-budget excess, weak paired confidence, missing/drifting provider-observed identity, non-distinct grader, regression, insufficient trials, or resource-policy failure. An eligible result never authorizes promotion: human approval and the version bump remain separate gates.
