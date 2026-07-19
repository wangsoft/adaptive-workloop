# Provider CLI Adapters

The bundled adapters make the same provider-neutral request executable through local Codex and Claude Code CLIs:

- `evals/adapters/codex-cli`
- `evals/adapters/claude-code`

They create `artifact_root/project`, optionally copy a case fixture from `<WORKLOOP_FIXTURE_ROOT>/<case-id>`, verify the bound Skill digest, and install only that Skill at the host's project-local path. `bare` installs nothing and rejects a pre-seeded adaptive-workloop path. Fixture and Skill symlinks are rejected.

Both adapters require `WORKLOOP_ADAPTER_MODEL`; `WORKLOOP_ADAPTER_EFFORT` defaults to `high`. Provider timeout defaults to 240 seconds and combined JSONL output to 1 MiB. Override them with `WORKLOOP_PROVIDER_TIMEOUT` and `WORKLOOP_PROVIDER_MAX_OUTPUT_BYTES`, then name every override with `scripts/run-evals --pass-env`.

## Codex

The Codex adapter uses ephemeral execution, ignores user config, keeps project exec-policy rules active, applies `workspace-write`, requests JSONL events plus a JSON Schema-constrained final result, and never enables the sandbox-bypass flag.

```bash
export WORKLOOP_ADAPTER_MODEL=gpt-5.6-sol
scripts/run-evals --suite behavior --condition candidate --trials 3 \
  --adapter evals/adapters/codex-cli \
  --model-profile codex-gpt-5.6-sol-high \
  --pass-env WORKLOOP_ADAPTER_MODEL \
  --pass-env CODEX_HOME \
  --allow-review-required \
  --output evals/runs/codex-candidate
```

Use `WORKLOOP_CODEX_BIN` only to pin a non-default executable. If an API-key or proxy configuration is required, pass each necessary name explicitly. The adapter filters the nested CLI environment again, so unrelated parent secrets do not cross the boundary.

## Claude Code

The Claude Code adapter uses `--bare`, structured stream JSON, no session persistence, strict empty MCP configuration, safe automatic permissions, and no bypass mode. `--bare` leaves project Skills available while skipping user hooks, plugins, memory, keychain reads, and CLAUDE.md auto-discovery.

```bash
export WORKLOOP_ADAPTER_MODEL=claude-fable-5
scripts/run-evals --suite behavior --condition candidate --trials 3 \
  --adapter evals/adapters/claude-code \
  --model-profile claude-code-claude-fable-5-high \
  --pass-env WORKLOOP_ADAPTER_MODEL \
  --pass-env ANTHROPIC_API_KEY \
  --allow-review-required \
  --output evals/runs/claude-candidate
```

Use `WORKLOOP_CLAUDE_BIN` to pin another executable and `WORKLOOP_MAX_BUDGET_USD` to set the CLI budget. Bedrock, Vertex, Foundry, certificate, and proxy variables are forwarded only when the outer runner explicitly receives them.

## Evidence limits

The model returns artifact paths, never trusted hashes. The adapter rejects absolute paths, traversal, symlinks, missing/non-regular files, duplicates, and adapter-internal paths, then computes SHA-256 itself. Skill calls come only from provider event objects identifying the Skill tool; prose such as “I used adaptive-workloop” does not count.

Configured model/effort and provider-observed model are separate fields. Absence of an observed ID remains `null`. Deterministic tests use fake provider CLIs to verify command shape, isolation, trace extraction, and artifact hashing; they do not test authentication, network behavior, real model routing, or task quality.

For held-out evaluation, keep fixture repositories outside this checkout and pass their parent with `WORKLOOP_FIXTURE_ROOT`. The same fixture tree and provider envelope must be used for `bare`, the exact `--previous-skill` checkout, and `candidate`.
