# Progress — Add rounding to invoice totals with a regression test

episode: `20260720-022304-add-rounding-to-invoice` · route: **verified** · path: `.workloop/tracked/20260720-022304-add-rounding-to-invoice` · updated: 2026-07-20T02:23:04Z
<!-- Write for a reader with zero chat memory. Use file/line, command, artifact,
     digest, and event pointers instead of narrative. -->

## Verified state

- Phase: complete
- Verified true and evidence: `invoice-rounding-tests` is defined in `checks.json`
- Assumed / unknown: non-cent currencies remain out of scope
- Broken: none
- Current state.json status: complete

## Completed units

<!-- unit — paths/commit — check IDs — evidence path -->
- Invoice fixture and regression suite — `examples/fixtures/invoice-rounding/` — `invoice-rounding-tests` — `evidence/grading.json`

## Next actions

<!-- #1 must be a concrete command or edit another agent can execute. -->
1. Copy the example to a scratch checkout before re-running `verify-contract`.

## Decisions and reroutes

<!-- date — event kind — decision — one-line evidence -->
- 2026-07-20 — Route 2 remains sufficient because the check is deterministic and local.

## Blockers

- None.

## Not re-runnable

<!-- Migrations, sends, deploys, publications, or other external effects.
     Record target-system evidence and reconciliation instructions. -->
- None.

## Resume protocol

From the repository root, read `manifest.json` → `state.json` → `events.jsonl` → this file → `contract.md` → `checks.json`, then run `scripts/verify-contract examples/verified-invoice-rounding`. Re-verification beats recorded claims.
