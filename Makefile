.PHONY: check test eval-validate

check:
	./scripts/check

test:
	python3 -m unittest discover -s tests -v

eval-validate:
	./scripts/run-evals --validate
