# Eval Matrix and Promotion Protocol

`scripts/run-matrix` is the canonical reproducible path from case collection to a paired comparison. It executes `bare`, an exact `previous` Skill checkout, and the current `candidate` with one bound configuration.

## Bound inputs

Before the first provider call, `matrix-manifest.json` binds:

- suite, selected cases, trials, model/host profile, grader profile, timeouts, output limits, and explicitly passed environment-variable names;
- dataset path, SHA-256, origin, evidence class, and held-out flag;
- producer and grader executable runtime digests;
- previous and candidate Skill runtime digests;
- the matrix, runner, grader, and comparison script digests.

Environment values are never written. Provider credentials cross the boundary only when named with `--pass-env`, then are filtered again by the producer or grader adapter.

## Recovery model

Every stage writes `started`, `completed`, or `failed` to a self-digested append-only `events.jsonl` chain. Run artifacts live under `runs/<condition>/attempt-NNN`; comparisons live under `comparisons/attempt-NNN.json`. `--resume` first verifies the manifest, event chain, artifact self-digests, and completed-stage digest bindings.

An interrupted collection receives a new numbered attempt. If grading was interrupted after it began mutating a run directory, the source is recollected into a new attempt before grading resumes. Partial evidence is preserved for diagnosis and never overwritten. A changed dataset, adapter, grader, Skill, profile, limit, script, or environment-name set rejects resume.

`matrix-result.json` points to the exact completed run and comparison artifacts. It is written only after all three conditions are complete and comparable.

## Evidence classes

- `public`: repository-visible regressions or explicitly public external data.
- `held-in`: private cases available during iteration.
- `held-out`: proposer-blind private cases unavailable during implementation.

External datasets must include both `"evidence_class": "..."` and boolean `"held_out"`; these must match the CLI label. Only `held-out` uses `true`. File digest binding prevents substituting another dataset during independent grading.

## Promotion decision

`scripts/decide-promotion` consumes one or more self-digested comparison files plus `evals/promotion-policy.json`. The bundled policy requires public and held-out evidence, at least three trials per condition, candidate pass rate of at least 0.8, no pass-rate decline or paired loss against previous, and a bounded token ratio. Cost-ratio enforcement is optional because some CLI providers do not expose price evidence; set a numeric maximum to make missing cost evidence inconclusive.

Decision states are:

- `rejected`: at least one measured gate failed;
- `inconclusive`: required evidence or a required metric is missing;
- `eligible_for_human_approval`: every automatic gate passed.

No state authorizes release. Every decision records `promotion_authorized=false` and `human_approval_required=true`. Human sign-off, release notes, versioning, and publication remain separate actions under host and user authority.

## Interpretation limits

Fake CLI tests prove orchestration, isolation, evidence binding, interruption recovery, and policy semantics only. A real promotion requires paid/provider-authenticated runs with fixed model-plus-host profiles, a genuinely private proposer-blind dataset, an independent grader calibrated for the target corpus, and human review of both positive and negative evidence.
