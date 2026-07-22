# Goal and Plan gates

Read this before starting a v3 episode. `scripts/validate-intent-plan` is the executable contract; this document explains its intent.

## Goal Gate

`goal.json` uses `workloop-goal/1` and one status:

- `clear`: no blocking unknown remains.
- `assumption_bounded`: each unresolved item is non-blocking and carries an explicit assumption plus evidence needed.
- `needs_user`: execution stops until the decision owner resolves the blocker.

The Goal must name an observable outcome, at least one stable success-criterion ID, in-scope work, non-goals, constraints, risks, unknowns, and authority. Authority records a decision owner, actions already allowed, and actions requiring approval. It documents permission; it never grants it.

Ask a question only when the missing answer changes scope, acceptance, safety, cost, or an external action. Otherwise record a bounded assumption and its falsifier.

## Plan Gate

`plan.json` uses `workloop-plan/1`. Its mutable `route` is the current route; `manifest.json.route` is the immutable initial route. `status=ready` means the next step is executable and all of these are true:

1. Every Goal criterion is mapped to at least one bounded step and one ID in `checks.json`.
2. Every step has one deliverable, owner role, dependencies, check IDs, write scope, required capabilities, effect class, approval state, rollback, and stop boundary.
3. Dependencies reference real steps and form an acyclic graph.
4. Route and topology agree; reviewed/distributed verification ownership is distinct from execution ownership.
5. Steps in the same parallel group have non-overlapping write scopes.
6. The selected domain profile's Check dimensions are present.
7. Budget, retry limit, stop conditions, and fallback are explicit.

Plans may evolve after discovery. Revise Goal, current route, or Plan explicitly, rerun the gate, and record the reason in `contract.md` and the next `in_progress` event. A local episode that escalates to Distributed starts a new tracked episode and links the handoff; it does not pretend local state became durable. Do not silently reinterpret a failed criterion.

## Proportionality

Plan size must match task size (P6). The seven Plan-Gate conditions are satisfied *trivially* by a minimal plan, and that is the intended shape for bounded Verified work: a `clear` or `assumption_bounded` Goal with a single success criterion, and a single `single_agent` step whose one deliverable maps to that criterion and one check. Do not manufacture steps, agent roles, phases, or a coordinator the task does not need — inflating a bounded fix into a multi-phase project is exactly the over-process this skill exists to prevent. Add structure only when risk, horizon, or genuinely independent slices demand it; a heavier plan must be justified by the classification, not by habit.

## Dispatch envelope

Send a worker only its step plus the minimum repository pointers needed to execute it:

- Goal criterion IDs and deliverable;
- dependency artifacts and interface contracts;
- allowed write scope and capabilities;
- check IDs, effect class, approval status, rollback, budget, and stop condition.

The worker returns status, changed paths/artifacts, evidence, assumptions, residual risks, and blockers. It does not change the Goal, Plan, route, permissions, or Memory. The coordinator integrates one verified slice at a time.

Use `single_agent` for a bounded serial task, `producer_reviewer` when independent checking matters, `coordinator_workers` only after Route 4's Cost gate, and `durable_serial` when persistence matters but parallel dispatch does not pay.

## Legacy episodes

`workloop-episode/2` remains readable and keeps its previous lifecycle. New episodes use v3. Do not fabricate Goal/Plan history for a completed v2 episode; migrate only when resumed work needs a new decision boundary.
