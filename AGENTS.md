# Adaptive Workloop maintenance

This repository contains one installable Agent Skill. Keep the runtime small, deterministic, and replaceable.

## Source map

- `SKILL.md`: trigger and outer-loop contract; keep under 500 lines.
- `references/`: route, verification, long-running, and model-delta details.
- `scripts/`: Python 3.10+ deterministic controls; no network calls in package checks.
- `assets/`: episode templates copied by `create-episode`.
- `evals/`: public trigger, behavior, and regression cases plus adapter contract.
- `tests/`: public-interface security and lifecycle regressions.

## Change rules

- Write a failing behavior test before fixing script behavior.
- Never reintroduce executable commands in Markdown or `bash -c`/`shell=True` verification.
- Keep manifest immutable; mutate lifecycle through `episode-state` and append-only events.
- Public repository cases are regression tests, not held-out proof.
- Model-specific rules require measured model-plus-host evidence and expiry.
- Preserve one orchestration owner and do not let specialist Skills change Workloop route or authority.

## Completion gate

Run:

```bash
make check
```

For behavior promotion, additionally run paired bare/previous/candidate adapter trials and a private held-out suite. Record negative results; do not delete them to improve optics.
