# Domain verification profiles

Profiles define the minimum questions Check must answer. They do not prescribe a specialist Skill, grant capabilities, or make subjective evidence deterministic.

| Profile | Required dimensions | Typical evidence |
|---|---|---|
| `engineering` | tests, static-analysis, runtime-or-artifact, diff-scope | focused tests, lint/type check, real runtime or artifact inspection, contract-to-diff map |
| `research` | freshness, triangulation, citation-traceability, counterevidence | dated primary sources, independent corroboration, claim-to-source links, disconfirming evidence |
| `writing_design` | rubric, factuality, audience-fit, rendering-or-review | explicit rubric, fact check, target-reader pass, rendered artifact or human review |
| `personal_planning` | constraints, budget-or-resources, milestones, safety | stated constraints, cost/resource envelope, scheduled checkpoints, reversible/safe fallback |
| `high_stakes` | authoritative-sources, specialist-review, approvals, rollback | current authoritative guidance, qualified review, action-bound approval, recovery plan |

Choose the closest profile when creating an episode. Use `high_stakes` when medical, legal, financial, safety, production, destructive, or other consequential action requires a stricter boundary. A mixed task may include extra dimensions; never remove a required dimension to make the gate pass.

Non-engineering proof commonly belongs in `checks.json.manual`: make the attestation criterion concrete, name the reviewer, and link the reviewed artifact. A manual criterion remaining open means the episode is not complete.
