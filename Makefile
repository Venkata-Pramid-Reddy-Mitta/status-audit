# status-audit developer tasks. `make verify` is the single promise the README makes to a
# reviewer: it must pass from a fresh clone with no network access.

PYTHON ?= python3
export PYTHONPATH := src

.PHONY: help install lint test coverage experiments receipts report evidence verify generate clean

help:
	@echo "targets: install lint test coverage experiments receipts report evidence verify generate clean"

install:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	ruff check src tests tools experiments

test:
	$(PYTHON) -m pytest -q

coverage:
	$(PYTHON) -m pytest --cov=status_audit --cov-report=term-missing \
		--cov-report=json:reports/coverage.json --junitxml=reports/junit.xml -q

experiments:
	@for e in headline confession_lag threshold_sensitivity rollup_rule direction_split; do \
		$(PYTHON) experiments/exp_$$e.py; echo; \
	done

# receipts depends on coverage having produced reports/junit.xml and reports/coverage.json.
receipts: coverage
	$(PYTHON) tools/collect_metrics.py --skip-tests
	$(PYTHON) tools/check_numbers.py

report:
	$(PYTHON) -m status_audit.cli audit --html docs/report.html --json docs/report.json

generate:
	$(PYTHON) -m status_audit.generate

# Evidence needs the optional browser extra; it is not part of verify.
evidence:
	$(PYTHON) tools/render_diagrams.py
	$(PYTHON) tools/capture_screenshots.py
	$(PYTHON) tools/record_demo.py

verify: lint coverage receipts
	@echo "verify: OK"

clean:
	rm -rf reports .pytest_cache .ruff_cache .coverage coverage.json docs/report.html docs/report.json
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
