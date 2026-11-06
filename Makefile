PYTHON ?= .venv/bin/python
.PHONY: check test-contracts

check: test-contracts

test-contracts:
	@$(PYTHON) -m unittest discover -s tests/phase3/contracts -p 'test_*.py' -v
