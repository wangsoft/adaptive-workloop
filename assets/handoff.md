# Handoff — {{TASK}}

episode: `{{EPISODE_ID}}` · slice: <name> · created: {{DATE}}
<!-- One handoff = one slice = one worker (or one next-session). The receiver
     gets ONLY this file plus the repo — write it self-contained. -->

## Objective (this slice only)

<!-- One paragraph. An independently mergeable, independently verifiable outcome.
     If it's only useful after other slices land, it's not a slice — re-cut. -->

- Goal criterion IDs: <IDs from goal.json>
- Plan step ID: <ID from plan.json>
- Deliverable: <one reviewable artifact or change>

## Read first (≤5 pointers)

<!-- file:line — why it matters. Not a tour; the minimum to act safely. -->
-

## Constraints

- Owned write-set (may touch): <files/dirs>
- Must NOT touch: <files/dirs owned by other slices or the coordinator>
- Interfaces to honor: <types / API shapes / schemas, with file refs>
- Non-goals:
- Risk signals in play: <none | list — high-risk slices keep Reviewed discipline>
- Capability scope: <tools, paths, network, permissions; narrower than coordinator>
- Effect / approval: <workspace-local | external | irreversible> / <not-required | pending | approved>
- Rollback and stop condition: <how to undo; when to stop>
- Orchestration owner: <host-native | workloop coordinator; never nested>

## Verification

- Commands: <exact, non-interactive>
- Check IDs: <IDs from the slice checks.json or integration checks.json>
- Done when: <observable criteria and required manual attestations>

## Report back (worker fills on completion)

- Status: done | blocked — <why, one line>
- Diff summary / commits:
- Verification evidence: <command + output location — a claim is not evidence>
- Surprises / new risks:
- Proposed follow-ups (not acted on):
