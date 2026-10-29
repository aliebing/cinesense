.PHONY: dev-api dev-web test test-api test-web lint

dev-api:
	uv run uvicorn cinesense.api.app:create_app --factory --reload --port 8000

dev-web:
	cd web && npm run dev

test: test-api test-web

test-api:
	uv run pytest

test-web:
	cd web && npx vitest run

lint:
	uv run ruff check .
	cd web && npm run lint
