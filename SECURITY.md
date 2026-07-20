# Security

adaptive-workloop is a process-routing Skill. It **grants no permissions**: the
host, user, and repository policy remain the authoritative boundary for
filesystem, network, execution, credential, commit, and deployment access.

## Threat model

What the Skill defends against, and how:

| Threat | Mitigation |
|---|---|
| **Prompt injection via repo/web content** | The Skill instructs the host to treat retrieved content as data, and `verify-contract` accepts structured argv evidence rather than prose claims. Regression `rc-010` exercises this policy boundary; host isolation remains the enforcement boundary. |
| **Hollow verification** | `verify-contract` executes argv without a shell, constrains cwd, enforces timeouts, rejects unfilled episode templates, and detects common zero-test success output (`rc-008`). A `verified` transition requires a strict `workloop-grading/1` pass bound to the current checks and per-check evidence; `complete` revalidates its digest. |
| **Unauthorized irreversible actions** | Push, publish, migrate, delete, deploy, payment, and message-send always require action-bound user approval in the current session, regardless of model capability claims (`rc-004`). |
| **Capability/authority confusion** | Demonstrated capability may enlarge step size, never permissions or gates (P4). |
| **Malicious model overlays** | Model-delta entries may only add ≤3-line counter-instructions; entries that touch routes, gates, or permissions are rejected (`rc-003`). |
| **Self-modification / eval gaming** | The Skill cannot edit its own evaluator, promotion policy, ledger, or protected surfaces. Promotion needs proposer-blind held-out evidence and human approval (P5, P6). |
| **Supply-chain drift** | Runtime is standard-library-only Python; CI pins third-party Actions and validator versions. Deterministic release archives carry a SHA-256 checksum, and plugin/protocol surfaces participate in the Skill runtime digest. |
| **Evidence tampering** | New episode manifests are bound to `episode.created`; verification events bind grading and per-check evidence, and completion rejects later drift. Release and eval artifacts are digest-bound and provider logs are redacted. |

Redaction and sandboxing here are **defense in depth, not complete DLP**. The
host sandbox and permission model remain the real enforcement boundary.

## Scope and limits

- The verifier is not a sandbox. It reduces footguns; it does not contain a
  hostile command. Run untrusted work under host-level isolation.
- Log redaction matches explicit secret values and common patterns only. Do not
  rely on it to scrub arbitrary secrets from adapter output.
- Hollow-green detection recognizes common test-runner output and explicit
  `output_must_match` assertions; it is not a universal test-coverage oracle.
- Episodes created before manifest binding remain legacy evidence. Recreate or
  independently review them before relying on immutable-manifest claims.
- Deterministic CI uses fake CLIs only and makes no real-model quality claim.

## Reporting a vulnerability

Report suspected vulnerabilities privately to the maintainer (open a GitHub
security advisory or a minimal private report) rather than a public issue.
Please include a reproduction and the affected version/commit. We aim to
acknowledge within a few days. Do not include real secrets in a report.
