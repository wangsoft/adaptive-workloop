<div align="right"><strong>English</strong> | <a href="./README.zh-CN.md">中文</a></div>

# adaptive-workloop

**A risk-based process router for non-trivial AI coding work.** It decides how much planning, verification, independent review, durability, and coordination a task deserves, while specialist Skills keep ownership of phase-local technique.

> Process is a cost. Spend it where failure is expensive and remove it where the bare model already succeeds.

Status: **0.4.0 candidate**. Deterministic package, integrity, security, evidence-class binding, isolated independent graders, resumable three-condition matrices, fail-closed promotion decisions, provider adapters, CI, and Codex-standalone regressions are implemented. Real-model proposer-blind held-out evidence is still required before stable promotion.

## When it activates

Use it for multi-step work involving ambiguity, high-risk surfaces, weak verification, independent review, multiple sessions, or model/host capability differences. It also resumes existing `.workloop` episodes and handles explicit process-routing requests.

Ordinary one-step edits, isolated bug fixes, standalone reviews, Q&A, and prose remain on the host's normal fast path.

## Routes

| Route | Use when |
|---|---|
| **Direct** | Explicit invocation reveals trivial, reversible work whose diff is sufficient proof. |
| **Verified** | Deterministic checks exist or are cheap to add; no high-risk signal. |
| **Reviewed** | High risk, subjective completion, or weak/missing deterministic proof. |
| **Distributed** | Work must survive restarts, or independent slices pass the multi-Agent Cost gate. |

Workloop owns route, gates, budgets, state, and orchestration. Delegated Skills own only the assigned phase. Choose one orchestration owner—host-native or Workloop Route 4—and avoid recursive worker trees.

## Safety and evidence

Routes 2–4 create an episode containing an immutable manifest, mutable state, append-only events, human-readable contract, and structured `checks.json`.

Checks use argv arrays rather than shell strings:

```json
{
  "schema": "workloop-checks/1",
  "checks": [{
    "id": "tests",
    "description": "targeted tests pass",
    "argv": ["python3", "-m", "pytest", "tests/test_feature.py"],
    "cwd": ".",
    "timeout_seconds": 120,
    "expected_exit": 0,
    "output_must_match": ["[1-9][0-9]* passed"],
    "risk": "workspace-local"
  }],
  "manual": []
}
```

The verifier executes without a shell, constrains cwd to the repository, enforces timeouts, prints successful output, and writes grading artifacts. Repository snapshots hash file contents rather than only dirty path labels. Append-only events are the durable write-ahead record; a stale `state.json` cache is reconciled from the validated event chain before the next transition. Host sandbox, permissions, network policy, and user approval remain authoritative; verification is not a permission bypass.

## Install

`adaptive-workloop` is the only required Skill for Codex. Waza, Superpowers, gstack, and mattpocock/skills are lineage and optional specialist sources—not runtime dependencies. Missing specialists use host-native fallbacks and are never installed implicitly.

```bash
# local checkout
npx skills add ./adaptive-workloop

# or copy into the Codex Skill directory
cp -r adaptive-workloop ~/.codex/skills/
```

Codex UI metadata lives in `agents/openai.yaml`. Deterministic scripts require Python 3.10+ on macOS/Linux.

## Commands

```bash
# repository facts + optional host-only capability manifest
scripts/probe-capabilities . [--capabilities capabilities.json]

# routes 2–4; Distributed defaults to tracked durable state
scripts/create-episode --task "Add CSV importer" --route verified --model "unknown"

# after contract.md and checks.json are ready
scripts/episode-state .workloop/local/<episode-id> --status in_progress --kind work.started

# strict structured verification
scripts/verify-contract .workloop/local/<episode-id>

# append lifecycle event + update mutable state
scripts/episode-state .workloop/local/<episode-id> \
  --status verified --kind verification.passed --evidence evidence/grading.json

# scan the Git-visible surface of a Distributed episode without printing secrets
scripts/check-episode .workloop/tracked/<episode-id>

# package and eval validation
scripts/check
scripts/run-evals --validate

# four-route conformance with no optional specialist Skills
scripts/run-evals --suite standalone \
  --host-profile codex-standalone \
  --adapter <provider-adapter> \
  --output evals/runs/codex-standalone

# collect, independently grade, and compare all three conditions
export WORKLOOP_ADAPTER_MODEL=gpt-5.6-sol
export WORKLOOP_GRADER_MODEL=claude-fable-5
scripts/run-matrix --suite behavior --case bc-001 --trials 3 \
  --adapter evals/adapters/codex-cli \
  --grader evals/adapters/claude-grader \
  --grader-profile claude-code-fable-5-high \
  --previous-skill /path/to/adaptive-workloop-v0.3.0 \
  --model-profile codex-gpt-5.6-sol-high \
  --pass-env WORKLOOP_ADAPTER_MODEL --pass-env CODEX_HOME \
  --pass-env WORKLOOP_GRADER_MODEL --pass-env ANTHROPIC_API_KEY \
  --output evals/matrices/public

# resume after an interrupted stage without overwriting prior attempts
scripts/run-matrix <same arguments> --resume

# a private dataset must self-label consistently and remain outside this checkout
scripts/run-matrix --suite behavior \
  --dataset /private/evals/behavior-held-out.json \
  --evidence-class held-out <same provider and matrix arguments> \
  --output evals/matrices/held-out

# policy output can only become eligible_for_human_approval, never auto-promoted
scripts/decide-promotion --policy evals/promotion-policy.json \
  --comparison evals/matrices/public/comparisons/attempt-001.json \
  --comparison evals/matrices/held-out/comparisons/attempt-001.json \
  --output evals/matrices/promotion-decision.json
```

## Storage

- Verified/Reviewed: `.workloop/local/` is ignored runtime state.
- Distributed: `.workloop/tracked/` keeps redacted manifest/state/events/contract/checks/progress/handoff visible to Git; runtime, capability snapshots, and evidence remain ignored.
- `.workloop/proposals/` is not ignored, so accepted improvement proposals can survive review.

An ephemeral workspace still needs an external issue/task store before claiming durable execution.

## Layout

```text
adaptive-workloop/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── probe-capabilities
│   ├── create-episode
│   ├── verify-contract
│   ├── episode-state
│   ├── check-episode
│   ├── run-evals
│   ├── grade-evals
│   ├── compare-evals
│   ├── run-matrix
│   ├── decide-promotion
│   └── check
├── references/
├── assets/
│   ├── contract.md
│   ├── checks.json
│   ├── progress.md
│   └── handoff.md
├── evals/
│   ├── trigger-cases.json
│   ├── behavior-cases.json
│   ├── regression-cases.json
│   ├── standalone-cases.json
│   ├── profiles/codex-standalone.json
│   ├── adapters/codex-cli
│   ├── adapters/claude-code
│   ├── adapters/codex-grader
│   ├── adapters/claude-grader
│   ├── promotion-policy.json
│   ├── matrix-protocol.md
│   ├── grader-contract.md
│   └── adapter-contract.md
└── tests/
```

## Evaluation

`scripts/run-evals` validates all public suites and can execute a provider-neutral adapter. Every run writes a self-digested manifest binding the Skill checkout, adapter runtime, full dataset, evidence class, selected cases, condition, model/host profile, trial count, limits, and explicitly passed environment names. Repository datasets are always `public`. An external dataset requires an explicit matching `--evidence-class`, a matching `evidence_class` field, and a consistent boolean `held_out`; mismatches fail closed. Adapter subprocesses inherit a deny-by-default environment, bounded combined output, one timeout covering stdin and execution, and process-group cleanup. Requests never include expected labels.

Trigger routing and standalone conformance are graded exactly. Standalone artifacts must exist under the runner-owned `artifact_root` and match SHA-256 values computed by the adapter from regular files; model-supplied hashes and path claims are not trusted. Behavior and regression outputs remain review-required and exit 3 unless an explicit collection stage uses `--allow-review-required`. `scripts/grade-evals` verifies every source digest, rejects a grader whose runtime digest matches the producer, and writes separate review artifacts without replacing original grading. `scripts/compare-evals` accepts only compatible, completed runs and reports pass rate, Wilson interval, pass@k, pass^k, usage, duration, and paired candidate deltas.

`evals/adapters/codex-cli` and `evals/adapters/claude-code` materialize only the bound candidate/previous Skill into an isolated case workspace; `bare` receives none. They use each CLI's structured-output mode, derive artifact hashes locally, and derive Skill calls from provider event instrumentation rather than model prose. The bundled Codex and Claude graders run in fresh temporary workspaces; Codex is read-only and ignores project rules, while Claude disables tools, slash commands, persistence, and non-explicit MCP. Configured and provider-observed grader identities stay separate.

`scripts/run-matrix` is the canonical three-condition orchestrator. It binds scripts, adapters, grader, dataset, candidate/previous Skill digests, profiles, limits, and environment names before execution. Its self-digested append-only event chain and numbered attempts let `--resume` continue after interruption without overwriting partial evidence. `scripts/decide-promotion` consumes self-digested comparisons and a strict policy, checks required public/held-out classes, trial counts, pass rate, paired regressions, and resource ratios, and returns `rejected`, `inconclusive`, or `eligible_for_human_approval`. It always records `promotion_authorized=false`.

Credentials, fixture roots, and model configuration must be named explicitly with `--pass-env`; see `evals/provider-adapters.md` and `evals/matrix-protocol.md`. CI exercises all adapters against fake CLIs only—no real model call or quality claim is made by the deterministic suite.

The standalone suite fixes `installed_skills=[]`, `subagents=false`, and `browser=false`; it covers all four routes, rejects any trace that calls an unavailable Skill, and requires the high-risk no-verifier path to stop at `needs_human`. This proves fallback wiring, not real-model quality.

Run the same fixtures separately for `bare`, an exact `--previous-skill` checkout, and `candidate`, with the same model, host, effort, tools, repository snapshot, grader, and runtime envelope. Use repeated trials and compare verified success, pass^k, human intervention, latency, cost, rollback, and incidents.

Repository cases are public regressions, not held-out proof. Stable promotion requires a private held-out suite unavailable to the proposer.

GitHub CI runs the deterministic gate and pinned Ruff checks on Python 3.10, 3.12, and 3.14 on Linux, plus Python 3.12 on macOS. The runtime package itself remains standard-library-only.

## Model policy

Routing never branches on model brand. Unknown models receive the same routes and authority with tighter verification cadence. Measured model-plus-host deltas may add short, expiring counter-instructions; the active ledger ships empty. A clean streak can enlarge increments only inside its current episode.

## Lineage

The design combines harness-engineering's empirical controls, Waza's restraint, Superpowers' independent verification, gstack's runtime discipline, and mattpocock/skills' composability—without copying their full workflows or depending on those packages.

## License

MIT
