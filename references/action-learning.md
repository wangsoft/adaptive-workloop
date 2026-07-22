# Act and controlled learning

Act closes the PDCA cycle without letting the executor rewrite its own rules or the user's Memory.

## Branches

1. **Task action:** close when Goal evidence passes; otherwise repair, reroute, revise Goal/Plan, or hand off within the episode.
2. **Skill candidate:** use only for a repeated, generalizable failure in routing, gating, dispatch, verification, recovery, or learning policy. Evaluate it later through `references/improvement.md` in a separate episode.
3. **Project or Memory candidate:** retain a durable fact only when it is evidence-bound, scoped, useful beyond this episode, non-secret, deduplicated, and reviewable.

Do not create a learning candidate merely because an implementation failed once. First classify the failure as an implementation bug, specification gap, noise, or ambiguity. Prefer task repair for one-off failures.

## Candidate record

`scripts/record-learning` appends `workloop-learning/1` events to `learning-candidates.jsonl`. Each event includes the claim, evidence paths and digests, episode provenance, writer, scope, generalizability, sensitivity, confidence, dedupe key, optional expiry, review requirement, and a hash-chain link.

The script has no approval or promotion command. `status` remains `candidate`, `promotion.requires_explicit_approval` remains true, `promotion.performed` remains false, and secret candidates are rejected. A digest proves which evidence was referenced; it does not prove the claim is true.

## Retention and promotion

- Episode state and candidate events may be recorded automatically inside the episode.
- Project learning requires project-owner review and belongs in a project-defined durable store.
- User-level Memory requires an explicit user request plus a host-specific adapter. Never assume that writing `memory.md`, `MEMORY.md`, a home-directory file, or a remote knowledge base is authorized.
- Skill changes require the separate proposal, protected-surface, held-out evaluation, and human approval protocol.

Before promotion, re-check provenance, current validity, sensitivity, duplication, scope, expiry, and whether the claim survived another episode. Rejected or expired candidates remain auditable; they are not silently deleted or treated as instructions.
