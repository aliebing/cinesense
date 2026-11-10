.PHONY: up down logs dev-api dev-web test test-api test-web lint db-init ingest eval admin-password

# Python commands run in backend/ (its own pyproject and .venv); the frontend lives in frontend/.
API = cd backend && uv run
SUPABASE = npx supabase --workdir database

# Own local Supabase (database/supabase/config.toml, ports 5532x): `up` starts it, applies database/schema.sql as
# migration, then builds and starts the app (api, web, proxy).
up:
	$(SUPABASE) start
	docker compose up -d --build
	@echo "CineSense: http://localhost:8080  ·  Supabase Studio: http://localhost:55323"

down:
	docker compose down
	$(SUPABASE) stop

logs:
	docker compose logs -f --tail 50

dev-api:
	$(API) uvicorn cinesense.web_api.app:create_app --factory --reload --port 8000

dev-web:
	cd frontend && npm run dev

test: test-api test-web

test-api:
	$(API) pytest

test-web:
	cd frontend && npx vitest run

# bcrypt hash of a new /admin password, printed as the TECH_PASSWORD_HASH line for .env
admin-password:
	cd backend && uv run python -m cinesense.web_api.admin_session

lint:
	$(API) ruff check .
	cd frontend && npm run lint

db-init:
	$(API) python -m cinesense.catalog_import.pipeline --init-schema --no-films

ingest:
	$(API) python -m cinesense.catalog_import.pipeline

eval:
	$(API) python -m cinesense.evaluation
