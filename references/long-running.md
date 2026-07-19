# Long-Running Work

Use for Route 4 and any task that may outlive the current context. Assume the process can stop after every line.

## Episode package

| Artifact | Role | Mutation rule |
|---|---|---|
| `manifest.json` | start facts: task, route, model/host, Skill digest, repository anchor, runtime/capability digests | immutable |
| `state.json` | materialized lifecycle status and last event sequence | update only through `episode-state`; treat as a repairable cache |
| `events.jsonl` | authoritative ordered state/reroute/checkpoint history | append-only write-ahead record |
| `contract.md` | intent, scope, risks, interfaces, budgets | edit only with a recorded scope-change event |
| `checks.json` | structured automatic checks and manual attestations | review changes; digest captured at verification |
| `progress.md` | verified truth, next action, assumptions, non-rerunnable effects | update every boundary |
| `evidence/` | check outputs and grading | generated; bounded retention |

`create-episode` stores Verified/Reviewed work under ignored `.workloop/local/`. Distributed defaults to `.workloop/tracked/`; runtime/capability snapshots, lock files, and evidence remain ignored, while manifest/state/events/contract/checks/progress/handoff can survive Git-based handoff. `episode-state` validates the complete event sequence and status chain, repairs a stale state cache from its last durable event, and blocks `complete` until `check-episode` passes the redaction gate. If the workspace itself is ephemeral, configure an external issue/task store before claiming durability.

## Checkpoint and resume

Checkpoint before risky work, after every verified unit, before compaction, and at worker shutdown. Record exact next action, verified truth versus assumptions, failures already tried, budgets remaining, and external effects that must not be replayed.

Resume in this order:

1. Resolve the installed Skill and read manifest → state → events → progress → contract → checks.
2. Compare repository head, content-based snapshot digest, active workers/workspaces, and target-system effects with the record.
3. Re-run `verify-contract <episode-dir>` before trusting a previous green.
4. Correct stale progress and append a resume event.
5. Announce episode, phase, orchestration owner, and next bounded action.

## Coordinator and workers

- Apply the Route 4 Cost gate before parallelizing.
- Give every worker one vertical outcome, isolated workspace, non-overlapping write set, bounded capabilities, exact checks, and one handoff.
- Pass artifact pointers and task-local context, not the coordinator transcript or credentials.
- Integrate one verified slice at a time. Shared schemas, exports, route tables, and migration order belong to the coordinator or a dedicated integration slice.
- Use one orchestration owner and keep delegation depth at one level unless an eval proves deeper hierarchy worthwhile.

## Recovery and external effects

- Retry only classified transient failures, within attempt/time/token/cost budgets.
- Record non-idempotent work in `progress.md` with idempotency key or reconciliation query.
- Cancellation is a state transition: stop new calls, revoke child capabilities, reconcile in-flight effects, then append evidence.
- A missing heartbeat, corrupted state, or incompatible snapshot stops dispatch. Rebuild from manifest, events, repository state, and target systems before continuing.
- Stop cleanly when budget is exhausted, verification is impossible, or the contract is wrong. Produce updated progress, an event, and a self-contained handoff instead of an unverified finish.
