---
name: adaptive-workloop
description: "Risk-routed, evidence-gated work orchestrator: process scales to task risk, completion is proven with falsifiable and auditable evidence instead of claims, routing stays brand-blind across models, and demonstrated capability never expands authority. A Goal→Plan→Do→Check→Act loop wraps four routes (Direct, Verified, Reviewed, Distributed) for a multi-step engineering task or other non-trivial research, writing/design, planning, or operational work. Use when work needs goal clarification, an executable plan, risk-based routing, agent-role dispatch, independent verification, multiple sessions, controlled learning, or adaptation to model/host capabilities; when resuming a .workloop episode; or when the user asks how work should proceed (怎么开工, 目标是否清楚, 计划是否可行, 要不要分配 agent, 如何检查结果, 该走什么流程). Not for one-step edits, ordinary isolated bug fixes, standalone reviews, pure Q&A, translations, explanations, or one-shot prose drafting."
license: MIT
metadata:
  version: "0.7.0"
  compatibility: "Host-agnostic instructions; deterministic scripts require Python 3.10+ on macOS/Linux."
  status: "candidate — Goal/Plan gates, dispatch contracts, profile-aware verification, and candidate-only learning pass deterministically; independent architecture review and real-model private evidence are still required before stable promotion"
---

# Adaptive Workloop

Route non-trivial work through a Goal-gated PDCA loop that can prove completion and preserve useful learning without silently expanding authority. It is the default orchestrator; installed specialist Skills accelerate only the phase that needs them and remain optional.

Specialists are optional accelerators, never dependencies.

## Boundaries and precedence

1. Host, user, and repository permissions remain authoritative; this skill grants nothing.
2. Workloop owns route, gates, budgets, episode state, and orchestration choice.
3. A delegated agent or specialist owns only its typed step and write scope. It may not silently change Goal, route, Plan, spawn nested workers, commit, push, publish, migrate, delete, or promote Memory.
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
| P6 | Keep process proportional to task risk; delete rules that show no held-in uplift or cause public/private regression. |

## Workloop

```text
probe -> Goal Gate -> classify/route -> Plan Gate -> Dispatch/Do -> Check -> Act
```

### 0. Probe

From the repository root, or from a chosen artifact/workspace root for non-repository work, run:

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

### 1. Goal Gate

Before planning or editing, make `goal.json` decision-ready:

- `clear`: outcome, success criteria, scope/non-goals, constraints, risks, unknowns, and authority are explicit.
- `assumption_bounded`: unresolved items are non-blocking, written as falsifiable assumptions, and paired with evidence needed.
- `needs_user`: a blocking ambiguity, missing decision owner, or authority gap remains. Stop and ask only the blocking question.

Do not turn a vague request into a large inferred project. Every success criterion needs an observable proof path. Read `references/goal-plan.md` for the schema and gate.

### 2. Classify

Use anchored evidence:

| Axis | Lower | Higher |
|---|---|---|
| Reversibility | git-only, trivial revert | migration, release, production or external effect |
| Blast radius | one concern, few files | public API, auth, payments, security, many consumers |
| Verifiability | a check can falsify the change | subjective result or missing seam |
| Horizon | one session, serial | survives restart or has independent slices |

Any auth, payment, personal-data, migration/deletion, security-boundary, public-contract, release, or production-infrastructure change is high risk.

Select the domain verification profile at creation time: `engineering`, `research`, `writing_design`, `personal_planning`, or `high_stakes`. Profiles change evidence dimensions, not permissions; read `references/domain-profiles.md`.

### 3. Route

| Route | Entry |
|---|---|
| **1 Direct** | Explicit invocation reveals trivial, reversible work whose diff is sufficient proof. |
| **2 Verified** | Deterministic checks exist or are cheap to add; no high-risk signal. |
| **3 Reviewed** | High risk, subjective completion, or weak/missing deterministic verification. |
| **4 Distributed** | Work outlives one session, or independent slices pass the cost gate in `references/routes.md`. |

When two routes qualify, choose the lower only when failure is cheaply reversible. Announce route and evidence in one line. Read only that route in `references/routes.md`; Route 4 also reads `references/long-running.md`.

### 4. Plan Gate and contract

Routes 2–4 create an episode before the first edit:

```bash
<skill-dir>/scripts/create-episode \
  --task "<one-line outcome>" \
  --route <verified|reviewed|distributed> \
  --profile <engineering|research|writing_design|personal_planning|high_stakes> \
  --model "<honest self-id>" \
  [--capabilities <host-manifest.json>]
```

Verified/Reviewed episodes default to ignored `.workloop/local/`; Distributed episodes default to durable `.workloop/tracked/`. Fill and validate:

- `goal.json`: observable outcome, typed criteria, scope, risks, unknowns, and authority.
- `plan.json`: topology, owners, dependency DAG, bounded steps, deliverables, criterion/check mappings, write scopes, capabilities, approvals, rollback, budget, stop conditions, and fallback.
- `contract.md`: intent, scope, risk, non-goals, interfaces, and verifier attack target.
- `checks.json`: structured argv checks and manual attestations. Freeform shell strings are invalid.
- `progress.md`: verified truth, assumptions, next action, and non-rerunnable effects.

Run `<skill-dir>/scripts/validate-intent-plan <episode-dir>`. It passes only when each Goal criterion maps to a step and check, the DAG is acyclic, domain verification dimensions are covered, review ownership is independent where required, and parallel write scopes do not overlap. A plan is sufficient when its next step is executable; it need not predict every future detail.

Read `references/goal-plan.md` and `references/verification.md`. After both gates pass, start execution with `<skill-dir>/scripts/episode-state <episode-dir> --status in_progress --kind work.started`. A v3 start event binds Goal, Plan, and checks digests.

### 5. Dispatch and Do

- Read before editing; make the smallest coherent diff; keep WIP at one bounded unit.
- Select topology deliberately: `single_agent`, `producer_reviewer`, `coordinator_workers`, or `durable_serial`. Agent roles are Plan data, not automatic permission to spawn.
- Dispatch each step with its Goal criteria, deliverable, dependencies, write scope, capabilities, check IDs, effect class, approval state, rollback, and stop condition. Return evidence, changed paths, residual risks, and status.
- Discover specialist Skills through the host capability interface at phase time. Delegate only that step's technique; when none exists, execute the route's host-native fallback directly.
- Run the narrowest falsifying check after each meaningful increment.
- Route 4 checkpoints before risky work and at every slice boundary.
- Never hide irreversible actions inside verification commands. Run them through the host with action-bound approval.

One coordinator owns integration. Default agent depth is one; a worker may not create another worker. When dispatch cost exceeds its value or capabilities are unavailable, preserve the same Plan and execute `durable_serial` with WIP=1.

### 6. Check and Act

```bash
<skill-dir>/scripts/verify-contract <episode-dir>
<skill-dir>/scripts/episode-state <episode-dir> --status verified --kind verification.passed --evidence evidence/grading.json
<skill-dir>/scripts/episode-state <episode-dir> --status complete --kind episode.closed
```

Check is profile-aware and strict: every Goal criterion has evidence, every automatic check passes, every manual criterion is attested, command output is visible, and `evidence/grading.json` exists. The grading artifact binds Goal, Plan, and checks digests. The verifier rejects unfilled episode templates and common zero-test greens. The `verified` event binds per-check evidence and grading; `complete` revalidates it. It executes argv without a shell, constrains cwd to the workspace root, enforces timeouts, and refuses external-risk checks unless explicitly allowed. It is not a sandbox; host policy remains the enforcement boundary.

Before a tracked Distributed episode can enter `complete`, `episode-state` enforces the redacted Git-visible surface with `scripts/check-episode`. It reports rule and location, never the matched value. `events.jsonl` is the durable write-ahead record; each state transition validates its sequence and status chain, then repairs a stale `state.json` cache before continuing.

Any failure triggers a bounded fix and rerun. Two consecutive full-cycle failures, doubled scope, a newly discovered high-risk surface, user-contested quality, or a task crossing the session boundary reroutes upward and records an event.

For high-risk work without an independent verifier, a labeled self-review may prepare a draft but cannot promote an irreversible action. Require a fresh session, human review, or another independent verifier before promotion.

Act has three explicit branches:

1. **Task action:** close, repair, reroute, revise Goal/Plan, or hand off.
2. **Skill candidate:** record a repeated, generalizable orchestration failure, then evaluate it only in a separate improvement episode.
3. **Memory candidate:** record evidence, provenance, scope, confidence, sensitivity, dedupe key, and expiry. Never write directly to host Memory or `memory.md`; promotion requires an explicit user-approved host adapter.

Use `<skill-dir>/scripts/record-learning` only for reviewable candidates. It appends a digest chain and performs no promotion. Read `references/action-learning.md` for retention and promotion boundaries.

## Trace evidence mining

When a Harness improvement depends on many agent traces or a corpus too large for direct context, read `references/trace-evidence.md` and run the deterministic `scripts/analyze-traces` baseline first. A `bounded_rlm_candidate` result only asks the existing Cost gate and capability boundary whether one-level, read-only evidence delegation is justified; it never changes route or authority. Keep direct analysis as the fallback, validate every report against the original digest-bound traces, and pass only cited failure clusters into the separate improvement protocol.

## Model adaptation

Record the actual model, host, effort, capabilities, tool surface, and Skill digest in each episode. Apply an entry from `references/model-deltas.json` only when its evidence and expiry match that model-plus-host profile; read `references/model-deltas.md` for policy. Otherwise use the same routes with tighter verification cadence. An in-episode clean streak may enlarge increments for that episode; it does not create a persistent model profile.

## Improvement protocol

The Skill may record one typed, bounded Skill candidate; it never edits itself during the originating task (P5). Promotion is a separate, human-run episode: freeze a `workloop-improvement-proposal/2`, then bind four evidence classes (`public`, `held-in`, `held-out`, `audit-held-out`) through a validated proposal, an append-only search ledger, and a fail-closed `decide-promotion` gate that still leaves human approval and the version bump as separate steps (P6).

Full procedure, commands, and the protected-surface list: `references/improvement.md`.

## File map

| Need | Read or run |
|---|---|
| Goal, Plan, coverage gate, dispatch envelope | `references/goal-plan.md`, `scripts/validate-intent-plan` |
| Domain-specific Check dimensions | `references/domain-profiles.md` |
| Route playbook, specialist precedence, cost gate | `references/routes.md` |
| Check schema and evidence | `references/verification.md` |
| Act branches, Skill/Memory candidates | `references/action-learning.md`, `scripts/record-learning` |
| Large or cross-run trace evidence | `references/trace-evidence.md`, `scripts/analyze-traces`, `evals/trace-analysis-contract.md` |
| Resume, storage, handoff, recovery | `references/long-running.md` |
| Measured model behavior | `references/model-deltas.md`, `references/model-deltas.json` |
| Codex-only compatibility | `evals/profiles/codex-standalone.json`, `evals/standalone-cases.json` |
| Episode lifecycle and tracked-state redaction | `scripts/create-episode`, `scripts/episode-state`, `scripts/check-episode` |
| Deterministic release, manifest, and checksum | `scripts/package-skill`, `packaging.allowlist` |
| Self-improvement procedure and protected surfaces | `references/improvement.md`, `evals/proposal-contract.md`, `evals/editable-surfaces.json`, `scripts/validate-proposal` |
| Collection, sealed private evaluation, search accounting, comparison, promotion | `scripts/run-matrix`, `scripts/run-sealed-matrix`, `scripts/search-ledger`, `scripts/run-evals`, `scripts/grade-evals`, `scripts/compare-evals`, `scripts/decide-promotion`, `evals/matrix-protocol.md` |
