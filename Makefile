PY_SCRIPTS := scripts/check scripts/check-episode scripts/compare-evals scripts/create-episode scripts/decide-promotion scripts/episode-state scripts/grade-evals scripts/probe-capabilities scripts/run-evals scripts/run-matrix scripts/verify-contract scripts/workloop_core.py
PY_ADAPTERS := evals/adapters/claude-code evals/adapters/claude-grader evals/adapters/codex-cli evals/adapters/codex-grader evals/adapters/provider_common.py

.PHONY: check test lint eval-validate

check:
	./scripts/check

test:
	python3 -m unittest discover -s tests -v

lint:
	ruff check $(PY_SCRIPTS) $(PY_ADAPTERS) tests
	ruff format --check $(PY_SCRIPTS) $(PY_ADAPTERS) tests

eval-validate:
	./scripts/run-evals --validate
