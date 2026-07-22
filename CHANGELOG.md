# Changelog

All notable changes to adaptive-workloop. The format follows
[Keep a Changelog](https://keepachangelog.com/); versions are release candidates
until real-model held-out evidence supports a stable tag (see
[SECURITY.md](SECURITY.md) and the README evaluation section).

## [Unreleased]

### Changed
- The runtime now uses Goal-gated PDCA: v3 episodes block execution until
  `goal.json` and `plan.json` pass criterion/check coverage, DAG, ownership,
  profile, budget, and parallel-write gates. Legacy v2 episodes remain readable.
- The implicit scope now covers non-trivial engineering, research,
  writing/design, personal planning, and operations while retaining the fast
  path for one-step edits, Q&A, translation, and one-shot drafting.
- P6 now makes process proportionality explicit. Public evals distinguish
  bounded Verified work from Direct work with observable scope facts and exact
  single-step assertions; subjective completion uses named, auditable
  attestation instead of decorative deterministic checks.
- Installation docs now use the published `wangsoft/adaptive-workloop` GitHub
  source for Codex, Agent Skills hosts, and the Claude Code marketplace.

### Fixed
- `scripts/check` and `make test` no longer write `__pycache__` into the
  checkout (`PYTHONDONTWRITEBYTECODE`), keeping the package pristine and content
  hashes stable across machines; the regression now compares pre/post cache
  state instead of failing on unrelated pre-existing caches.
- Episode manifests now use the same canonical Skill runtime digest as release,
  proposal, and matrix evidence.
- Episode state can no longer enter `verified` or `complete` without a current,
  strict grading artifact and digest-bound per-check evidence.
- Packaged releases now retain every runtime protocol referenced by `SKILL.md`
  and can run their own deterministic integrity check without source tests.

### Added
- Domain verification profiles, typed agent dispatch envelopes, Goal/Plan
  digest binding, and an append-only `record-learning` candidate log. Skill
  changes still require the separate improvement protocol; Memory candidates
  are never promoted without explicit user-approved host integration.
- Optional recursive trace evidence mining: a SHA-256-bound OTLP JSONL baseline,
  stable trace/span citations, semantic failure clusters, report validation,
  one-level RLM candidacy gate, provider-neutral contract, public fixtures, and
  a direct fallback with no HALO or provider dependency.
- `make regen-example` safely rebuilds the sample through the real lifecycle so
  its manifest, events, grading, and per-check evidence stay digest-consistent;
  timestamps and durations intentionally remain volatile.
- Isolated the Claude Code plugin validation into its own CI job with a longer
  timeout; added concurrency cancellation to save CI minutes.
- GitHub PR/issue templates; suite versions remain independent dataset
  revisions rather than mirroring the Skill release.
- Claude Code plugin manifest (`.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`) so the Skill installs via
  `/plugin marketplace add` alongside the existing Codex path.
- Typed proposal validation, protected editable surfaces, sealed held-out and
  audit-held-out matrices, append-only whole-search accounting, paired
  confidence, observed-model identity gates, and promotion-policy v2.
- Deterministic `package-skill` releases with a self-describing file manifest,
  reproducible zip, and SHA-256 checksum.
- `make check-spec` and a CI job validate `SKILL.md` against the Agent Skills
  specification with `skills-ref`.
- CI pins current third-party Actions to reviewed commit SHAs and avoids
  repeating the full test suite already run by `make check`.
- `packaging.allowlist` and `make package` build a runtime-only release
  artifact (excludes tests, CI, dev contracts, caches).
- `references/improvement.md` holds the full self-improvement procedure; the
  `SKILL.md` section is now a short pointer.
- Trigger description restored concrete English and Chinese phrases; documented
  the no-Python fallback (route still applies, evidence recorded by hand).
- `examples/` adds a replayable, digest-bound sample episode and fixture.
- `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`.

## [0.4.0] — 2026
### Added
- Governed promotion-policy v1 with public/held-out evidence binding,
  independent graders, resumable bare/previous/candidate matrices, and a
  fail-closed decision gate that never auto-authorizes promotion.

## [0.3.0] — 2026
### Added
- Closed the deterministic eval loop: provider-neutral adapters, independent
  graders, immutable role-separated eval evidence.

## [0.2.2] — 2026
### Added
- Compatibility and static-analysis CI gates.
### Fixed
- Durable episode state is recoverable from the append-only event chain.
- Eval outcomes and artifacts made trustworthy (digest-bound, redacted).

## [0.2.1] — 2026-07-18
### Added
- First deterministic-package baseline: four-route router (Direct, Verified,
  Reviewed, Distributed), structured `checks.json`, shell-free verifier,
  episode lifecycle, model-delta policy with an empty ledger, and public
  trigger/behavior/regression/standalone suites.
