.PHONY: up down logs dev-api dev-web test test-api test-web lint db-init ingest eval

# Own local Supabase (supabase/config.toml, ports 5532x): `up` starts it and applies db/schema.sql as migration.
up:
	npx supabase start
	docker compose up -d --build
	@echo "CineSense: http://localhost:8080  ·  Supabase Studio: http://localhost:55323"

down:
	docker compose down
	npx supabase stop

logs:
	docker compose logs -f --tail 50

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

db-init:
	uv run python -m cinesense.ingest.pipeline --init-schema --no-films

ingest:
	uv run python -m cinesense.ingest.pipeline

eval:
	uv run python -m cinesense.eval
