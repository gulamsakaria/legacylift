.PHONY: install test lint demo demo-verify clean

install:
	pip install -e ".[dev]"

test:
	pytest -q --cov=legacylift --cov-report=term-missing

lint:
	ruff check src tests
	black --check src tests

demo:
	legacylift run examples/legacy-school-portal --doc examples/MIGRATION_NOTES.md

demo-verify:
	docker compose up -d db
	legacylift run examples/legacy-school-portal --doc examples/MIGRATION_NOTES.md
	docker compose down

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache *.egg-info build dist
