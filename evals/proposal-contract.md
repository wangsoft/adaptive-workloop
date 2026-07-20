# Improvement Proposal Contract

`workloop-improvement-proposal/2` turns an observed failure into one bounded candidate. It is a proposal and evidence-binding format, not permission to edit, evaluate private data, or release.

## Control boundary

The proposer may select exactly one entry from `editable-surfaces.json` and one exact hook inside that surface. The package digest and diff include the public case files plus evaluator-relevant adapters, profiles, registry, and policy; the registry protects all scripts, provider/grader adapters, host profiles, the registry itself, and the promotion policy. Every surface requires human review. Host/user permissions, the evaluator, the private-data broker, and the final promotion gate remain outside the optimized loop.

`scripts/validate-proposal` compares exact previous and candidate Skill checkouts. It computes actual runtime-path changes and rejects a no-op, an undeclared path, a protected path, multiple surfaces, a stale Skill digest, a proposal digest mismatch, or held-out exposure before freeze.

## Required JSON shape

```json
{
  "schema": "workloop-improvement-proposal/2",
  "proposal_id": "route-review-001",
  "decision": "evaluate",
  "created_at": "2026-07-19T12:00:00+08:00",
  "base_skill_digest": "sha256:<previous-runtime-digest>",
  "candidate_skill_digest": "sha256:<candidate-runtime-digest>",
  "failure_signature": {
    "terminal_cause": "under_routed_high_risk_change",
    "criticality": "root_cause",
    "agent_mechanism": "routing_rule_selection",
    "evidence_case_ids": ["held-in-017"],
    "evidence_artifact_digests": ["sha256:<artifact-digest>"]
  },
  "change": {
    "mechanism_family": "routing_rule",
    "surface_id": "skill.route.policy",
    "exact_hook": "routes.reviewed.entry",
    "summary": "Route public authorization changes to Reviewed.",
    "candidate_values": {
      "routes.reviewed.entry": "Add public authorization boundary to high-risk entry."
    },
    "expected_affected_cases": ["held-in-017"],
    "protected_passing_cases": ["t-001", "bc-001"],
    "regression_guard": "Public and standalone suites remain non-regressing.",
    "why_not_noop": "The prior rule selected Verified for the observed case.",
    "decline_reason": null
  },
  "search": {
    "round": 1,
    "candidate_index": 1,
    "candidates_considered": 1,
    "held_out_evaluations_before_freeze": 0,
    "audit_held_out_evaluations_before_freeze": 0
  },
  "budgets": {
    "max_trials": 120,
    "max_cost_usd": 50.0,
    "max_duration_seconds": 14400
  },
  "changed_paths": ["SKILL.md"],
  "digest": "sha256:<canonical-json-digest-without-digest-field>"
}
```

Identifiers are lowercase letters/digits plus `.`, `_`, and `-`. `criticality` is one of `root_cause`, `contributor`, `unknown`, `non_terminal_friction`, or `recovered_friction`. Evidence must identify both the cases and immutable artifact digests that motivated the proposal.

`candidate_values` contains exactly the selected hook; it is an auditable claim about the intended mechanism, not a patch language. `changed_paths` must exactly equal the validator-computed runtime diff. The candidate index and search round bind the search history; `candidates_considered` counts failed candidates too.

For a `decline` decision, previous and candidate digests must match, `changed_paths` must be empty, `candidate_values` must be `{}` or `null`, and `decline_reason` must explain why no bounded change is justified.

## Digest and validation

The proposal digest is SHA-256 over compact canonical JSON with sorted keys and the top-level `digest` field omitted. The repository helper exposes the exact implementation:

```bash
PYTHONPATH=scripts python3 -c 'import json,sys; from workloop_core import canonical_json_digest; p=json.load(sys.stdin); print(canonical_json_digest(p, omit={"digest"}))' < proposal.json
```

Insert that value, then validate:

```bash
scripts/validate-proposal \
  --proposal proposal.json \
  --registry evals/editable-surfaces.json \
  --previous-skill /path/to/previous \
  --candidate-skill /path/to/candidate \
  --output /private/evals/proposal-validation.json
```

The resulting `workloop-proposal-validation/1` is self-digested and binds the validator implementation, registry file, proposal file, previous/candidate runtime digests, actual changed paths, validators, search state, and budgets. `run-matrix` invokes the current validator and requires it to reproduce the entire attestation before collection; `decide-promotion` requires the same frozen binding across all four evidence classes and a closed Search Ledger that selects the same proposal and candidate.

`candidates_considered` and `round` include rejected candidates. Record every candidate comparison in `scripts/search-ledger` and close each candidate explicitly as `rejected` or `selected`. Promotion v2 compares the proposal counters with that ledger and aggregates trial, reported cost, duration, and private exposure across every recorded comparison, including rejected candidates. Work that occurred outside the ledger remains unaccounted evidence and invalidates any claim that the budget covers the full search.
