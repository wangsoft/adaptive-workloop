# Eval Matrix and Promotion Protocol

`scripts/run-matrix` is the canonical reproducible path from case collection to a paired comparison. It executes `bare`, an exact `previous` Skill checkout, and the current `candidate` with one bound configuration. Improvement candidates also bind a frozen `workloop-proposal-validation/1` attestation; see `proposal-contract.md`.

## Bound inputs

Before the first provider call, `matrix-manifest.json` binds:

- suite, selected cases, trials, model/host profile, grader profile, timeouts, output limits, and explicitly passed environment-variable names;
- dataset path, SHA-256, origin, evidence class, and held-out flag;
- producer and grader executable runtime digests;
- previous and candidate Skill runtime digests;
- the matrix, runner, grader, comparison, and proposal-validator script digests;
- when supplied, the proposal, editable-surface registry, validator, exact changed paths, search counters, and evaluation budgets.

Environment values are never written. Provider credentials cross the boundary only when named with `--pass-env`, then are filtered again by the producer or grader adapter.

The output root is owner-only (`0700`) and one non-blocking `.matrix.lock` prevents two matrix writers from sharing it. JSON and text evidence is written through same-directory temporary files, `fsync`, and atomic replace with owner-only (`0600`) artifact permissions. Provider/grader stdout and stderr are redacted using explicitly passed sensitive names/values plus common secret patterns before persistence. This reduces accidental disclosure; it is not complete DLP, and model output must still be treated as untrusted private evidence.

## Recovery model

Every stage writes `started`, `completed`, or `failed` to a self-digested append-only `events.jsonl` chain. Run artifacts live under `runs/<condition>/attempt-NNN`; comparisons live under `comparisons/attempt-NNN.json`. `--resume` first verifies the manifest, event chain, artifact self-digests, and completed-stage digest bindings.

An interrupted collection receives a new numbered attempt. If grading was interrupted after it began mutating a run directory, the source is recollected into a new attempt before grading resumes. Partial evidence is preserved for diagnosis and never overwritten. A changed dataset, adapter, grader, Skill, profile, limit, script, or environment-name set rejects resume.

`matrix-result.json` points to the exact completed run and comparison artifacts. It is written only after all three conditions are complete and comparable.

## Evidence classes and exposure order

- `public`: repository-visible regressions or explicitly public external data.
- `held-in`: target cases available during bounded candidate iteration; this class must demonstrate the claimed uplift.
- `held-out`: proposer-blind private cases unavailable during implementation and evaluated at most once after proposal freeze.
- `audit-held-out`: a separate proposer-blind one-shot final audit, withheld until the candidate has passed the other gates.

External datasets must include `"evidence_class": "..."`, boolean `"held_out"`, and an `"audit_holdout"` boolean when used for the audit. These must match the CLI label. Both private held-out classes use `held_out=true`; only `audit-held-out` uses `audit_holdout=true`. File digest binding prevents substituting another dataset during independent grading.

The recommended order is public and held-in iteration, proposal freeze, one held-out comparison, then one audit-held-out comparison. A proposal whose search counters claim either private class was exposed before freeze is invalid.

## Sealed private-data broker

Use `scripts/run-sealed-matrix` for both private classes. It rejects a dataset that is inside the Skill checkout, overlaps the output root, is a symlink/non-regular file, has group/world permission bits, or has inconsistent evidence labels. It owns the dataset, evidence-class, proposal-validation, and output arguments so nested matrix arguments cannot replace them.

```bash
chmod 0600 /private/evals/held-out.json
scripts/run-sealed-matrix \
  --dataset /private/evals/held-out.json \
  --evidence-class held-out \
  --proposal-validation /private/evals/proposal-validation.json \
  --output /private/results/held-out \
  -- <normal run-matrix arguments except broker-owned arguments>
```

This is a local path and permission boundary, not a remote confidentiality system. The host still owns filesystem isolation, credentials, process permissions, and access logs. A stronger deployment can place this same narrow broker contract in a separate service account or evaluation service without changing the matrix format.

## Promotion decision

`scripts/decide-promotion` consumes self-digested comparison files, a closed Search Ledger, and `evals/promotion-policy.json`. The bundled v2 policy requires one comparison for each of public, held-in, held-out, and audit-held-out; at least ten trials per condition; candidate pass rate of at least 0.8; no pass-rate decline or paired loss; held-in uplift of at least 0.05; positive paired net wins; and a configured lower bound on the Wilson 95% interval for candidate wins among discordant trials. It also caps candidate count, search rounds, one-shot private comparisons, token ratio, and cost ratio. Missing cost evidence is therefore inconclusive under v2 rather than silently ignored.

All final comparisons must bind the same validated proposal, previous Skill, and selected candidate Skill. The matrix asks the current validator to reproduce the attestation before any provider stage, rather than trusting writable JSON. Promotion also requires complete, stable provider-observed producer and grader identities, one frozen grader binding, and a grader observed-model ID distinct from the producer. Missing identity is inconclusive; drift or overlap fails. These are mechanical provenance checks, not proof of cognitive independence.

## Search Ledger

Create one ledger before the first candidate evaluation. Record every comparison immediately, then close each candidate as rejected or selected. Selection is terminal and all candidates must be closed before promotion:

```bash
scripts/search-ledger init \
  --ledger /private/results/search.jsonl \
  --search-id route-review-001 \
  --base-skill-digest sha256:<previous-skill-digest>
scripts/search-ledger record \
  --ledger /private/results/search.jsonl \
  --comparison /private/results/candidate-1/public/comparisons/attempt-001.json
scripts/search-ledger close \
  --ledger /private/results/search.jsonl \
  --candidate-skill-digest sha256:<candidate-1-digest> \
  --status rejected --reason "held-in uplift below threshold"
```

The owner-only JSONL file uses sequence numbers, previous-event digests, an exclusive append lock, and `fsync`. Validation reopens every comparison and detects artifact drift. It binds unique candidate indexes, proposal validation, proposal digest, base/candidate Skill digests, round, evidence class, and resource totals. The promotion gate compares proposal counters with the ledger and aggregates trials, reported cost, duration, and private exposure across selected and rejected candidates. The hash chain is tamper-evident for accidental edits and drift; it is not an external transparency log and cannot defeat a malicious file owner who rewrites and rehashes the entire ledger.

Pass the terminal ledger with `--search-ledger /private/results/search.jsonl`. The four `--comparison` arguments remain the selected candidate's final evidence set.

Decision states are:

- `rejected`: at least one measured gate failed;
- `inconclusive`: required evidence or a required metric is missing;
- `eligible_for_human_approval`: every automatic gate passed.

No state authorizes release. Every decision records `promotion_authorized=false` and `human_approval_required=true`. Human sign-off, release notes, versioning, and publication remain separate actions under host and user authority.

## Interpretation limits

Fake CLI tests prove orchestration, isolation, proposal/dataset binding, interruption recovery, and policy semantics only. A real promotion requires paid/provider-authenticated runs with fixed model-plus-host profiles, genuinely private and separate held-out/audit-held-out datasets, an independent grader calibrated for the target corpus, complete usage/cost evidence, and human review of both positive and negative evidence.
