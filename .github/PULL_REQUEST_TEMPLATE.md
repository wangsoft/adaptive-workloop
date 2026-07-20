<!-- Thanks for contributing to adaptive-workloop. Keep the runtime small,
     deterministic, and replaceable (see CONTRIBUTING.md). -->

## What and why

<!-- One or two sentences: the observed problem and the change. -->

## Type

- [ ] Docs / packaging / CI only
- [ ] Script or protocol fix (no behavior change to routing/verification)
- [ ] Behavior change to the Skill (requires the governance path below)

## Checks (must pass on a clean checkout)

- [ ] `make lint`
- [ ] `make check`
- [ ] `make check-spec`
- [ ] `make check-claude-plugin`
- [ ] Touched packaging → ran `make package`, verified the SHA-256, ran the packaged `scripts/check`
- [ ] Touched the sample episode → regenerated with `make regen-example`

## Behavior changes only

A behavior change cannot be self-approved. Confirm the governance path
(`CONTRIBUTING.md`, `references/improvement.md`):

- [ ] One typed `workloop-improvement-proposal/2`, single editable surface
- [ ] Public + held-in + held-out + audit-held-out evidence bound via the matrix
- [ ] `decide-promotion` returned `eligible_for_human_approval`; a human bumps the version

## Notes

<!-- Risks, follow-ups, or context for the reviewer. -->
