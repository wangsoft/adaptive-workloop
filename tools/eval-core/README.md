# Core-value A/B eval

**The question this answers:** does the *same model* produce better *outcomes*
**with** adaptive-workloop than **without** it? That is the evidence P6 demands
and that the governance suites (trigger/behavior/regression/standalone) do not
provide — those grade routing mechanics; this grades whether the code actually
works.

Maintainer tooling. Not shipped in the installed skill, not part of the runtime
digest surface.

## How it works

For each task the runner gives the identical prompt to the model twice — once
with no skill (`bare`), once with the skill installed (`workloop`) — each in a
fresh copy of the fixture. It drives the same provider adapters documented in
`evals/adapter-contract.md`.

Grading is **deterministic and outcome-based**: the fixture's own test must
pass. Before grading, each case's canonical test is restored from `graded/`
over the workspace, so a run cannot "pass" by deleting or weakening the test —
the skill's own hollow-green rule applied to the eval itself.

```
cases.json          task set: prompt + fixture + deterministic check
fixtures/<task>/     buggy source + the test the agent sees
graded/<task>/       canonical test, restored before grading (anti-tamper)
solutions/<task>/    reference fix — used ONLY by the oracle for --validate
run.py               the A/B runner (bare vs workloop, paired Wilson)
fake_adapter.py      oracle adapter for --validate (no model)
```

## Prove the plumbing (no credentials)

```bash
make eval-core-validate
```

The oracle solves every case identically for both conditions, so the run must
report `delta = 0`. It uses the same shared provider workspace contract as real
Codex/Claude runs. This proves fixture-copy → adapter → canonical-restore →
outcome-grade → paired comparison works end to end, with zero spurious uplift.

## Run the real comparison (needs a provider + credentials)

```bash
python3 tools/eval-core/run.py \
  --adapter python3 --adapter evals/adapters/codex-cli \
  --model-profile codex-gpt-5.6-sol-high \
  --trials 3 \
  --pass-env CODEX_HOME --pass-env WORKLOOP_ADAPTER_MODEL \
  --output /tmp/core-eval
```

Run the *same* command with `--adapter python3 --adapter evals/adapters/claude-code`
and a Claude profile to get a second provider. Use ≥3 trials for nondeterministic
models.

## Reading the result

`core-result.json` and the summary report, per condition: pass rate + Wilson 95%
interval; the pass-rate delta; and paired counts (workloop-only solved,
bare-only solved, net). What each outcome means:

- **workloop clearly ahead** (positive delta, net wins, non-overlapping
  intervals): first real evidence the skill earns its complexity. Keep it, and
  start deleting anything that didn't contribute (P6).
- **no difference**: the core idea isn't paying for its overhead on these tasks
  — either the tasks are too easy (bare already succeeds) or the process isn't
  helping. Harder/again with more trials, or simplify the skill.
- **workloop behind**: the process is a net drag; treat as a bug in the router,
  not a reason to add more machinery.

## Honesty caveats

- This is a small curated set; it bounds a hypothesis, it does not prove
  generality. Grow the task set and keep negative results.
- It is a *core-value* signal (skill vs no-skill), separate from the *promotion*
  pipeline (candidate skill vs previous skill) under `evals/` + `scripts/run-matrix`.
- Fixtures are self-contained and standard-library-only so the check is
  deterministic; real repositories are messier.
