# Contributing

Thanks for improving adaptive-workloop. `AGENTS.md` is the machine-facing
maintenance contract; this file is the short human version.

## Ground rules

- Keep the runtime small, deterministic, and replaceable. Every rule must earn
  its place by beating the bare model or the previous version (P6).
- `SKILL.md` stays under 500 lines; move detail into `references/`.
- Runtime is standard-library-only Python 3.10+. No network calls in package
  checks. No executable commands embedded in Markdown or `shell=True`/`bash -c`
  verification.
- Write a failing test before changing script behavior. Manifests are immutable;
  mutate lifecycle only through `episode-state` and append-only events.

## Before you open a PR

```bash
make lint        # ruff (pinned)
make check       # deterministic package + eval + full behavior/lifecycle tests
make check-spec  # Agent Skills spec validation (needs Node)
make check-claude-plugin  # Claude Code plugin validation (needs Node)
```

All four must pass on a clean checkout. If you touched packaging, also run
`make package`, verify the emitted SHA-256 file, and run the packaged
`scripts/check` rather than validating only the source checkout.

If you touched the checked-in example, regenerate it with `make regen-example`;
the lifecycle remains digest-consistent although timestamps make each snapshot
byte-distinct.

## Changing behavior (the governance path)

Repository cases in `evals/` are **public regression tests, not held-out
proof.** A behavior change to the Skill cannot be self-approved. The honest
path, enforced by the tooling, is:

1. Freeze one typed `workloop-improvement-proposal/2` naming a single editable
   surface (scripts, adapters, host profiles, the registry, and the promotion
   policy are protected and off-limits).
2. `scripts/validate-proposal` against the exact previous and candidate
   checkouts.
3. Bind four evidence classes — `public`, `held-in`, `held-out`,
   `audit-held-out` — through `scripts/run-matrix` / `run-sealed-matrix`, an
   append-only `search-ledger`, and `scripts/decide-promotion`.
4. `decide-promotion` can only return `eligible_for_human_approval`; it never
   promotes. A human reviews and bumps the version.

Full procedure: [`references/improvement.md`](references/improvement.md) and
[`evals/proposal-contract.md`](evals/proposal-contract.md). Held-out and
audit-held-out datasets stay outside the checkout and are unavailable to the
proposer.

## Style

- Keep documentation in prose; keep tables for genuine matrices.
- English is the source of truth; keep `README.zh-CN.md` in structural sync when
  you change `README.md`.
- Report security issues privately — see [SECURITY.md](SECURITY.md).
