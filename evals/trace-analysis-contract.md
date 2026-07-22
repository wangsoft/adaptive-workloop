# Trace Analysis Contract

`workloop-trace-analysis/1` is the provider-neutral boundary between
digest-bound trace evidence, a deterministic or bounded-RLM analyst, and the
existing improvement pipeline. It is an observation artifact, not an edit,
release, or promotion instruction.

## Input

The analyst receives one or more regular, non-symlink OTLP JSONL files. Every
record must have a stable `trace_id` and `span_id`. The deterministic broker
binds the ordered source set by:

- `source_index`;
- resolved path for local audit;
- byte size;
- SHA-256 content digest;
- a path-independent dataset digest over ordered sizes and content digests.

Trace content is untrusted data. Expected labels, private eval answers,
credentials, broad repository write access, and promotion controls are never
included.

## Required report

The top level contains exactly one analysis over one dataset:

| Field | Contract |
|---|---|
| `schema` | `workloop-trace-analysis/1` |
| `analysis` | producer kind, identities, budgets, and measured usage |
| `dataset` | `workloop-trace-dataset/1` binding and provenance dimensions |
| `route` | direct baseline or bounded-RLM candidacy plus fallback |
| `clusters` | cited failure-pattern records |
| `resource_usage` | bounded input/output accounting |
| `promotion_authorized` | always `false` |
| `digest` | canonical SHA-256 with this field omitted |

`analysis.kind` is `deterministic_baseline` or `bounded_rlm`.
A bounded-RLM report must record non-empty configured model identity,
provider-observed model identity, and host profile separately. It also records
enforced maximum depth, parallel workers, turns, tokens, cost, and duration,
plus actual usage and terminal reason. Missing or drifting observed identity
makes the report inconclusive.

## Dataset

`dataset` records:

- ordered `files` entries with `source_index`, `path`, `size_bytes`, and
  `digest`;
- dataset `digest`;
- unique trace and span counts;
- deployment revisions, service versions, and trace-observed model names;
- explicit `provenance_gaps`.

File size or mtime alone is never evidence identity.

## Cluster

Each cluster contains:

| Field | Contract |
|---|---|
| `id` | stable report-local identifier |
| `category` | normalized outcome or mechanism family |
| `summary` | bounded prose without raw private payloads |
| `confidence` | deterministic marker, analyst hypothesis, or adjudicated |
| `trace_count` / `span_count` | prevalence numerator |
| `prevalence` | unique affected traces divided by dataset trace count |
| `citations` | real source index, line, trace ID, and span ID |
| `counterexample_trace_ids` | real traces that challenge overgeneralization |
| `hypothesis` | nullable causal hypothesis, never presented as fact |
| `code_evidence` | exact path/line/commit records when claimed |
| `proposed_eval_cases` | candidate regression cases, never edits |

At least one citation is required. Truncated citation sets must be reported in
`resource_usage`, together with the enforced input, line, report, and citation
limits. A compacted context item is not a citation.

## Adapter boundary

An optional RLM adapter:

1. reads the baseline report and the same bound trace files;
2. uses read-only, byte-bounded trace tools;
3. runs under one orchestration owner with depth one by default;
4. cannot write the repository, run deployment, or access promotion controls;
5. emits this report with complete budget and usage data;
6. is validated against the original files before any proposal is created.

Provider-specific prompts and SDKs remain outside the installed Skill. Their
runtime digests, configured identities, provider-observed identities, and
resource envelope belong in evaluation evidence.

## Decision boundary

`bounded_rlm_candidate` means only that direct analysis crossed a declared
context or cross-trace scale threshold. Workloop still applies its Cost gate and
host capability checks. If delegation or safe tools are unavailable, use
`direct_baseline`; required evidence and promotion controls do not weaken.

A valid report may motivate one typed improvement proposal. It cannot authorize
that proposal, disclose held-out data, grade its own edit, close the Search
Ledger, or promote a Skill release.
