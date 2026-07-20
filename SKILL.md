---
name: adaptive-workloop
description: "Risk-based process router for a multi-step engineering task. Use when work needs execution routing across ambiguity, high-risk changes (auth, payments, data migration, public API, release), weak verification, independent review, multiple sessions, or model/host capability differences; when resuming a .workloop episode; or when the user explicitly asks how much process a task needs (how should we execute this, do we need independent review, is this change risky, 怎么开工, 该走什么流程, 要不要独立 review, 这个改动风险大吗). Not for one-step edits, ordinary isolated bug fixes, standalone reviews, pure Q&A, explanations, or prose-only writing."
license: MIT
metadata:
  version: "0.6.0"
  compatibility: "Host-agnostic instructions; deterministic scripts require Python 3.10+ on macOS/Linux."
  status: "candidate — append-only search accounting, private atomic evidence writes, observed-model identity gates, and human-only promotion pass deterministically; real-model private evidence is still required before stable promotion"
---

# Adaptive Workloop

Route non-trivial engineering work through the smallest loop that can prove completion. Delegate phase-local technique to installed specialists; do not copy their workflows here. Specialists are optional accelerators, never dependencies.

## Boundaries and precedence

1. Host, user, and repository permissions remain authoritative; this skill grants nothing.
2. Workloop owns route, gates, budgets, episode state, and orchestration choice.
3. A delegated specialist owns technique only inside its assigned phase. It may not silently change route, spawn nested workers, commit, push, publish, migrate, or delete.
4. Safety conflicts follow the more restrictive rule. Process-style conflicts return to Workloop ownership; do not use a generic "stricter workflow wins" rule.

Keep one orchestration owner. Choose host-native orchestration or Workloop Route 4, never both recursively.

Do not install, fetch, or enable a missing Skill during task execution unless the user explicitly asks. Use the host-native inline fallback in `references/routes.md`; missing specialists may reduce convenience, never the required evidence or safety boundary.

## Principles

| # | Rule |
|---|---|
| P1 | Route by observed capability and task risk, never model brand. |
| P2 | Unknown model or host is supported; use the conservative cadence. |
| P3 | Model deltas patch measured behavior only; they never replace routes or permissions. |
| P4 | Demonstrated capability may increase step size, never authority. |
| P5 | The skill may propose one typed, bounded improvement but may not edit its evaluator, permissions, promotion policy, or other protected control surfaces. |
| P6 | Delete rules that show no held-in uplift or cause public/private regression. |

## Workloop

```text
probe -> classify -> route -> contract -> execute -> verify -> record -> close or reroute
```

### 0. Probe

From the repository root, run:

```bash
<skill-dir>/scripts/probe-capabilities . [--capabilities <host-manifest.json>]
```

The script detects repository facts, verification commands, CI, runtimes, and host markers without scanning personal Skill directories. Its repository snapshot hashes tracked and untracked content while excluding `.git/` and `.workloop/`; a dirty-path label alone is not evidence of identical state. Supply host-only facts through a capability manifest:

```json
{
  "schema": "workloop-capabilities/1",
  "subagents": true,
  "browser": true,
  "context_budget": "ample",
  "effort_mode": "high",
  "permission_mode": "workspace-write",
  "native_orchestration": "host",
  "installed_skills": ["tdd", "review"]
}
```

Unknown fields or missing capabilities degrade the route; they do not grant authority or abort ordinary work.

If Python 3.10+ is unavailable, the scripts cannot run, but the router still applies (P2): classify and route from the tables below, keep the same gates, record contract criteria and their evidence by hand in the episode notes, and treat every verification claim under the same transcript-evidence rule. A missing runtime lowers convenience, never the evidence bar or authority.

To validate the minimum Codex-only installation, use `evals/profiles/codex-standalone.json`. It intentionally declares no optional specialist Skills, browser, subagents, or native orchestration so every fallback remains testable.

### 1. Classify

Use anchored evidence:

| Axis | Lower | Higher |
|---|---|---|
| Reversibility | git-only, trivial revert | migration, release, production or external effect |
| Blast radius | one concern, few files | public API, auth, payments, security, many consumers |
| Verifiability | a check can falsify the change | subjective result or missing seam |
| Horizon | one session, serial | survives restart or has independent slices |

Any auth, payment, personal-data, migration/deletion, security-boundary, public-contract, release, or production-infrastructure change is high risk.

### 2. Route

| Route | Entry |
|---|---|
| **1 Direct** | Explicit invocation reveals trivial, reversible work whose diff is sufficient proof. |
| **2 Verified** | Deterministic checks exist or are cheap to add; no high-risk signal. |
| **3 Reviewed** | High risk, subjective completion, or weak/missing deterministic verification. |
| **4 Distributed** | Work outlives one session, or independent slices pass the cost gate in `references/routes.md`. |

When two routes qualify, choose the lower only when failure is cheaply reversible. Announce route and evidence in one line. Read only that route in `references/routes.md`; Route 4 also reads `references/long-running.md`.

### 3. Create the contract

Routes 2–4 create an episode before the first edit:

```bash
<skill-dir>/scripts/create-episode \
  --task "<one-line outcome>" \
  --route <verified|reviewed|distributed> \
  --model "<honest self-id>" \
  [--capabilities <host-manifest.json>]
```

Verified/Reviewed episodes default to ignored `.workloop/local/`; Distributed episodes default to durable `.workloop/tracked/`. Fill:

- `contract.md`: intent, scope, risk, non-goals, interfaces, and verifier attack target.
- `checks.json`: structured argv checks and manual attestations. Freeform shell strings are invalid.
- `progress.md`: verified truth, assumptions, next action, and non-rerunnable effects.

Read `references/verification.md` for the schema and evidence rules.
After the contract is ready, start execution with `<skill-dir>/scripts/episode-state <episode-dir> --status in_progress --kind work.started`.

### 4. Execute

- Read before editing; make the smallest coherent diff; keep WIP at one bounded unit.
- Discover specialist Skills through the host capability interface at phase time. Delegate only that phase; when none exists, execute the route's host-native fallback directly.
- Run the narrowest falsifying check after each meaningful increment.
- Route 4 checkpoints before risky work and at every slice boundary.
- Never hide irreversible actions inside verification commands. Run them through the host with action-bound approval.

### 5. Verify, record, and close

```bash
<skill-dir>/scripts/verify-contract <episode-dir>
<skill-dir>/scripts/episode-state <episode-dir> --status verified --kind verification.passed --evidence evidence/grading.json
<skill-dir>/scripts/episode-state <episode-dir> --status complete --kind episode.closed
```

Close-out is strict: every automatic check passes, every manual criterion is attested, command output is visible, and `evidence/grading.json` exists. The verifier rejects unfilled episode templates and common zero-test greens. The `verified` event binds the current checks, per-check evidence, and grading digest; `complete` revalidates that binding. It executes argv without a shell, constrains cwd to the repository, enforces timeouts, and refuses external-risk checks unless explicitly allowed. It is not a sandbox; host policy remains the enforcement boundary.

Before a tracked Distributed episode can enter `complete`, `episode-state` enforces the redacted Git-visible surface with `scripts/check-episode`. It reports rule and location, never the matched value. `events.jsonl` is the durable write-ahead record; each state transition validates its sequence and status chain, then repairs a stale `state.json` cache before continuing.

Any failure triggers a bounded fix and rerun. Two consecutive full-cycle failures, doubled scope, a newly discovered high-risk surface, user-contested quality, or a task crossing the session boundary reroutes upward and records an event.

For high-risk work without an independent verifier, a labeled self-review may prepare a draft but cannot promote an irreversible action. Require a fresh session, human review, or another independent verifier before promotion.

## Model adaptation

Record the actual model, host, effort, capabilities, tool surface, and Skill digest in each episode. Apply an entry from `references/model-deltas.json` only when its evidence and expiry match that model-plus-host profile; read `references/model-deltas.md` for policy. Otherwise use the same routes with tighter verification cadence. An in-episode clean streak may enlarge increments for that episode; it does not create a persistent model profile.

## Improvement protocol

The Skill may propose one typed, bounded improvement; it never edits itself during a task (P5). Record observed routing or verification failures as you work, but make no Skill edit in that task. Promotion is a separate, human-run episode: freeze a `workloop-improvement-proposal/2`, then bind four evidence classes (`public`, `held-in`, `held-out`, `audit-held-out`) through a validated proposal, an append-only search ledger, and a fail-closed `decide-promotion` gate that still leaves human approval and the version bump as separate steps (P6).

Full procedure, commands, and the protected-surface list: `references/improvement.md`.

## File map

| Need | Read or run |
|---|---|
| Route playbook, specialist precedence, cost gate | `references/routes.md` |
| Check schema and evidence | `references/verification.md` |
| Resume, storage, handoff, recovery | `references/long-running.md` |
| Measured model behavior | `references/model-deltas.md`, `references/model-deltas.json` |
| Codex-only compatibility | `evals/profiles/codex-standalone.json`, `evals/standalone-cases.json` |
| Episode lifecycle and tracked-state redaction | `scripts/create-episode`, `scripts/episode-state`, `scripts/check-episode` |
| Deterministic release, manifest, and checksum | `scripts/package-skill`, `packaging.allowlist` |
| Self-improvement procedure and protected surfaces | `references/improvement.md`, `evals/proposal-contract.md`, `evals/editable-surfaces.json`, `scripts/validate-proposal` |
| Collection, sealed private evaluation, search accounting, comparison, promotion | `scripts/run-matrix`, `scripts/run-sealed-matrix`, `scripts/search-ledger`, `scripts/run-evals`, `scripts/grade-evals`, `scripts/compare-evals`, `scripts/decide-promotion`, `evals/matrix-protocol.md` |
