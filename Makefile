PY_SCRIPTS := scripts/check scripts/check-episode scripts/compare-evals scripts/create-episode scripts/decide-promotion scripts/episode-state scripts/grade-evals scripts/package-skill scripts/probe-capabilities scripts/run-evals scripts/run-matrix scripts/run-sealed-matrix scripts/search-ledger scripts/validate-proposal scripts/verify-contract scripts/workloop_core.py scripts/workloop_search.py
PY_ADAPTERS := evals/adapters/claude-code evals/adapters/claude-grader evals/adapters/codex-cli evals/adapters/codex-grader evals/adapters/provider_common.py
MAINTAINER_SCRIPTS := tools/regen-example

# Never write .pyc into the checkout; a stray __pycache__ fails the
# package-pristine test and perturbs content hashes over the tree.
export PYTHONDONTWRITEBYTECODE := 1

SKILL_REF_VERSION := 0.1.5
CLAUDE_CODE_VERSION := 2.1.191
DIST_DIR := dist
DIST_NAME := adaptive-workloop
.PHONY: check check-spec check-claude-plugin test lint eval-validate package regen-example

check:
	./scripts/check

check-spec:
	npx -y skills-ref@$(SKILL_REF_VERSION) validate .

check-claude-plugin:
	npx -y @anthropic-ai/claude-code@$(CLAUDE_CODE_VERSION) plugin validate .

test:
	python3 -m unittest discover -s tests -v

lint:
	ruff check $(PY_SCRIPTS) $(PY_ADAPTERS) $(MAINTAINER_SCRIPTS) tests
	ruff format --check $(PY_SCRIPTS) $(PY_ADAPTERS) $(MAINTAINER_SCRIPTS) tests

eval-validate:
	./scripts/run-evals --validate

# Build a deterministic, checksummed release from packaging.allowlist. The
# packaged copy validates its own manifest and progressive-disclosure closure.
package:
	./scripts/package-skill --output "$(DIST_DIR)"
	"$(DIST_DIR)/$(DIST_NAME)/scripts/check"
	npx -y skills-ref@$(SKILL_REF_VERSION) validate "$(DIST_DIR)/$(DIST_NAME)"
	npx -y @anthropic-ai/claude-code@$(CLAUDE_CODE_VERSION) plugin validate "$(DIST_DIR)/$(DIST_NAME)"

# Maintainer-only: rebuild the sample through the real lifecycle. Authored inputs
# remain the source of truth; volatile timestamps make the snapshot byte-distinct.
regen-example:
	./tools/regen-example
