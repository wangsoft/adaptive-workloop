# Handoff — Add rounding to invoice totals with a regression test

episode: `20260720-022304-add-rounding-to-invoice` · route: **verified**

## Objective (this slice only)

Not applicable. Route 2 is executed serially by one orchestration owner.

## Read first (≤5 pointers)

- `contract.md` — outcome and scope
- `checks.json` — executable regression criterion

## Constraints

- Owned write-set (may touch): none; no slice was delegated
- Must NOT touch: all repository files during example inspection
- Interfaces to honor: `workloop-checks/1`
- Non-goals: distributed execution
- Risk signals in play: none
- Capability scope: read-only inspection and local verification
- Orchestration owner: workloop coordinator

## Verification

- Commands: `scripts/verify-contract examples/verified-invoice-rounding`
- Check IDs: `invoice-rounding-tests`
- Done when: the grading artifact records a strict pass

## Report back (worker fills on completion)

- Status: done — no delegated slice was required
- Diff summary / commits: not applicable
- Verification evidence: `evidence/grading.json`
- Surprises / new risks: none
- Proposed follow-ups (not acted on): none
