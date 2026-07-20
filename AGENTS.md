# Adaptive Workloop maintenance

This repository contains one installable Agent Skill. Keep the runtime small, deterministic, and replaceable.

## Source map

- `SKILL.md`: trigger and outer-loop contract; keep under 500 lines.
- `references/`: route, verification, long-running, and model-delta details.
- `scripts/`: Python 3.10+ deterministic controls; no network calls in package checks.
- `assets/`: episode templates copied by `create-episode`.
- `evals/`: public cases, proposal/editable-surface contracts, evidence classes, adapters, and promotion policy.
- `tests/`: public-interface security and lifecycle regressions.
- `tools/`: maintainer-only generators excluded from the installed package.

## Change rules

- Write a failing behavior test before fixing script behavior.
- Never reintroduce executable commands in Markdown or `bash -c`/`shell=True` verification.
- Keep manifest immutable; mutate lifecycle through `episode-state` and append-only events.
- Public repository cases are regression tests, not held-out proof.
- Improvement candidates change one registered editable surface; scripts, provider/grader adapters, host profiles, the registry, and promotion policy remain protected controls.
- Freeze and validate the proposal before any held-out exposure. Keep held-out and audit-held-out datasets outside this checkout.
- Record every comparison and rejected candidate in one append-only Search Ledger; never reconstruct total search cost from only the selected candidate.
- Treat matrix output as private evidence: preserve its exclusive lock, atomic writes, owner-only permissions, and redacted provider logs.
- Model-specific rules require measured model-plus-host evidence and expiry.
- Preserve one orchestration owner and do not let specialist Skills change Workloop route or authority.

## Completion gate

Run:

```bash
make lint
make check
make check-spec
make check-claude-plugin
```

If packaging changed, also run `make package`, verify the emitted SHA-256 file,
and execute the packaged `scripts/check`. A source-checkout pass is not release
artifact evidence.

For behavior promotion, bind one validated proposal across paired bare/previous/candidate public, held-in, held-out, and audit-held-out comparisons. Run both private classes through `scripts/run-sealed-matrix`, record all candidates in `scripts/search-ledger`, and enforce the v2 search/resource/confidence/observed-identity policy. Retain negative results. Automatic eligibility never replaces human approval.
