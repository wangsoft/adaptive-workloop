# Progress — {{TASK}}

episode: `{{EPISODE_ID}}` · route: **{{ROUTE}}** · path: `{{EPISODE_PATH}}` · updated: {{DATE}}
<!-- Write for a reader with zero chat memory. Use file/line, command, artifact,
     digest, and event pointers instead of narrative. -->

## Verified state

- Phase:
- Verified true and evidence:
- Assumed / unknown:
- Broken:
- Current state.json status:

## Completed units

<!-- unit — paths/commit — check IDs — evidence path -->
-

## Next actions

<!-- #1 must be a concrete command or edit another agent can execute. -->
1.

## Decisions and reroutes

<!-- date — event kind — decision — one-line evidence -->
-

## Blockers

-

## Not re-runnable

<!-- Migrations, sends, deploys, publications, or other external effects.
     Record target-system evidence and reconciliation instructions. -->
- none

## Resume protocol

Resolve the installed `adaptive-workloop` Skill directory. Read `manifest.json` → `state.json` → `events.jsonl` → this file → `contract.md` → `checks.json`. Compare recorded state with `git status` and repository history since `manifest.repo.head`; then run `<skill-dir>/scripts/verify-contract {{EPISODE_PATH}}`. Re-verification beats recorded claims. Update this file and append an event before continuing.
