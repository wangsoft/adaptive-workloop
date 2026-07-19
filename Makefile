PY_SCRIPTS := scripts/check scripts/check-episode scripts/create-episode scripts/episode-state scripts/probe-capabilities scripts/run-evals scripts/verify-contract scripts/workloop_core.py

.PHONY: check test lint eval-validate

check:
	./scripts/check

test:
	python3 -m unittest discover -s tests -v

lint:
	ruff check $(PY_SCRIPTS) tests
	ruff format --check $(PY_SCRIPTS) tests

eval-validate:
	./scripts/run-evals --validate
