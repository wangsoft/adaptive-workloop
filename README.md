<div align="right"><strong>English</strong> | <a href="./README.zh-CN.md">中文</a></div>

# adaptive-workloop

**A risk-based process router for non-trivial AI coding work.** It decides how much planning, verification, independent review, durability, and coordination a task deserves, while specialist Skills keep ownership of phase-local technique.

> Process is a cost. Spend it where failure is expensive and remove it where the bare model already succeeds.

Status: **0.2.1 candidate**. Deterministic package, security, and Codex-standalone regressions are implemented; a real-model bare/previous/candidate behavior matrix is still required before stable promotion.

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

The verifier executes without a shell, constrains cwd to the repository, enforces timeouts, prints successful output, and writes grading artifacts. Host sandbox, permissions, network policy, and user approval remain authoritative; verification is not a permission bypass.

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

# package and eval validation
scripts/check
scripts/run-evals --validate

# four-route conformance with no optional specialist Skills
scripts/run-evals --suite standalone \
  --host-profile codex-standalone \
  --adapter <provider-adapter> \
  --output evals/runs/codex-standalone
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
│   ├── run-evals
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
│   └── adapter-contract.md
└── tests/
```

## Evaluation

`scripts/run-evals` validates all public suites and can execute a provider-neutral adapter. Requests never include expected labels. Trigger routing and standalone conformance are graded exactly; behavior and regression outputs remain review-required until an independent grader evaluates output, state, artifacts, and trace.

The standalone suite fixes `installed_skills=[]`, `subagents=false`, and `browser=false`; it covers all four routes, rejects any trace that calls an unavailable Skill, and requires the high-risk no-verifier path to stop at `needs_human`. This proves fallback wiring, not real-model quality.

Run the same fixtures separately for `bare`, `previous`, and `candidate`, with the same model, host, effort, tools, repository snapshot, and runtime envelope. Use repeated trials and compare verified success, pass^k, human intervention, latency, cost, rollback, and incidents.

Repository cases are public regressions, not held-out proof. Stable promotion requires a private held-out suite unavailable to the proposer.

## Model policy

Routing never branches on model brand. Unknown models receive the same routes and authority with tighter verification cadence. Measured model-plus-host deltas may add short, expiring counter-instructions; the active ledger ships empty. A clean streak can enlarge increments only inside its current episode.

## Lineage

The design combines harness-engineering's empirical controls, Waza's restraint, Superpowers' independent verification, gstack's runtime discipline, and mattpocock/skills' composability—without copying their full workflows or depending on those packages.

## License

MIT
