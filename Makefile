.PHONY: setup lint test

setup:
	python3 -m pip install -r requirements-dev.txt

lint:
	# Gate syntax and undefined-name errors first; broader style rules will be
	# enabled incrementally once the existing baseline is cleaned up.
	python3 -m ruff check --select E9,F63,F7,F82 app tests

test:
	python3 -m pytest -q
