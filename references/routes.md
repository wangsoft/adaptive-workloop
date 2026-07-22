# Execution Routes

Read only the selected route after reading this precedence section.

## Authority and precedence

- Host, user, and repository policy outrank every Skill.
- Workloop owns route, gates, episode state, budget, and orchestration.
- Specialists own phase-local technique only.
- One orchestration owner: select host-native orchestration or Workloop Route 4. Disable nested specialist delegation unless the outer owner explicitly allocates one bounded worker.
- Safety restrictions compose by taking the narrower authority. Workflow ceremony does not: Workloop's route remains authoritative.

Discover specialists through the host manifest or host tool search at the phase boundary. Do not infer a complete catalog by scanning and truncating home directories.

Agent roles are selected in `plan.json`; they are not spawned by default. Each dispatch receives one bounded step using the envelope in `goal-plan.md`. Workers may not edit Goal, Plan, route, policy, or Memory, and default maximum delegation depth is one. If dispatch is unavailable or uneconomic, keep the same ownership and verification boundaries under `durable_serial`.

| Phase | Specialist examples | Inline fallback |
|---|---|---|
| Alignment | brainstorming, think, grill, planning | Restate outcome, scope and open ambiguity; ask only blocking questions |
| Implementation | tdd, framework-specific implementation | One observable test/check, minimal implementation, repeat |
| Review | review, check, security review | Route 3 protocol |
| Release | ship, release | Verified artifact plus explicit approval for external action |

Use the inline host-native fallback whenever no listed specialist is available. A missing specialist changes phase technique, not route, evidence, or authority. Never install or fetch one implicitly during an episode.

## Route 1 — Direct

Use only after explicit Workloop invocation reveals that all are true:

- Git-only reversible change with no external effect.
- One concern, normally no more than three files.
- No public interface or high-risk signal.
- Diff readback or one obvious targeted check can falsify the edit.
- Comfortable fit in the current session.

State a one-line done criterion, make the smallest diff, run one obvious check if available, and show the diff. Do not create an episode or spawn a verifier. Escalate when scope reaches another subsystem, proof becomes ambiguous, or a high-risk signal appears.

## Route 2 — Verified

Use when deterministic checks exist or are cheap to add, no high-risk signal exists, and one agent/session is sufficient.

1. Create a local episode; pass Goal and Plan gates before editing.
2. For a bug, add a regression criterion that fails on the old behavior.
3. Implement one bounded increment; run the narrowest relevant check.
4. At a coherent boundary, run `verify-contract <episode-dir>`.
5. Before exit, trace every changed file to the contract and record verification evidence.

Without a TDD or implementation specialist, label the phase `host-native-verified` and run the same one-check -> minimal-change -> rerun loop directly.

No honest check means Route 2 is unavailable. Build the smallest seam first or use Route 3. Do not add unrelated repository-wide checks merely to look rigorous.

## Route 3 — Reviewed

Use for high-risk work, subjective completion, or weak/missing deterministic proof.

Follow Route 2 where checks exist, then run the `verification_owner_role` from `plan.json` with fresh context. Give it Goal criteria, Plan mappings, the contract, full diff/artifacts, repository pointers, and probe/capability summary—not the builder's rationale.

### Verifier protocol

1. **Compliance:** map every contract clause to evidence; identify gaps and scope drift.
2. **Attack:** provide a concrete input, state, sequence, trust boundary, or rollback failure for each finding. Findings need file/line evidence; a clean review is valid.
3. **Resolution:** critical findings block. Re-run affected checks after fixes and record accepted residual risks.

If no independent verifier exists, perform a `labeled-self-review`. That degraded path ends at `needs_human`: it may complete a reversible draft, but high-risk promotion or irreversible follow-through waits for a human or fresh independent session.

Exit requires strict contract PASS, resolved verifier findings, and action-bound user approval for push, publish, migrate, delete, deploy, payment, or message sending.

## Route 4 — Distributed

Use when work must survive session loss or independent slices create net value.

### Cost gate

All parallelization conditions must hold:

1. At least two slices can run independently with non-overlapping write sets.
2. Each worker has a concrete deliverable and deterministic or reviewable exit.
3. The communication artifact is smaller than the duplicated context and coordination cost.
4. Integration seams and merge order are explicit.
5. Parallel execution or independent attention provides measurable latency or quality value.

If the Cost gate fails, keep one agent and use `durable-serial` execution with durable serial slices. A long task may still use Route 4 for restart survival without parallel workers.

### Setup and loop

1. Create a tracked episode. Goal and Plan name integration criteria, slice interfaces, dependency order, budgets, and stop conditions.
2. Cut vertical, independently useful slices. Assign one isolated workspace and non-overlapping `write_scope` per worker; the Plan Gate rejects overlap inside a parallel group.
3. Give each worker a bounded handoff plus repository pointers. Child capabilities must be narrower than the coordinator's.
4. Integrate one verified slice at a time; re-run integration checks after each merge.
5. Append state transitions with `episode-state` and checkpoint `progress.md` before risk and at every boundary.

The orchestration owner coordinates, resolves shared interfaces, and integrates. It may execute a serial worker slice when no child agents exist, but must mark the role transition and preserve WIP=1. Avoid rigid coordinator ceremony when a single durable worker loop is cheaper.

Exit requires every slice integrated, strict integration PASS, state `complete`, and a handoff for anything deliberately left. Read `long-running.md` for resume and reconciliation.
