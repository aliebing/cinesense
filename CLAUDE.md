# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CineSense ("Don't choose a movie. Choose a feeling.") is a Turing College AI Engineering capstone: mood-based movie discovery with a cinematic, animated UI and a LangGraph chat agent grounded in real catalogue data (MovieLens, Wikidata, Wikipedia).

Local only (git-ignored, like `docs/video/` and the prompt drafts in `docs/`): the approved design is in `docs/superpowers/specs/2026-10-29-cinesense-design.md`. Read it before changing behaviour or look. Implementation plans and the 4-week roadmap are in `docs/superpowers/plans/`. Approved mockups are in `docs/superpowers/specs/mockups/`.

The grading briefs are in `docs/brief/` (`turing-college-capstone.md`, `turing-college-sprint4.md`). `ARCHITECTURE.md` is the reviewer-facing map of the code; keep it true when moving things.

## Conventions

- **Language:** UI text, code, identifiers, comments, commits and docs are all English. Talk to the user in German.
- **Look:** dark only, on a matte near-black ground, with fog and light on every page. The main stage is a wide (~2.25:1) cinema screen with letterbox bars and solid red side curtains; tune via the CSS variables at the top of `frontend/app/globals.css`. Text must stay readable over all effects.
- **Data:** never fabricate film facts. **No TMDB** (its terms forbid AI apps). Sources: MovieLens (local file, never commit it), Wikidata, Wikipedia, Streaming Availability API (1,000 req/month — every call goes through the cache/budget guard), optional YouTube Data API (90 searches/day plus status checks: embeddable, not blocked in Germany, not age-restricted).
- **External services** stay behind adapters (`backend/cinesense/data_sources/`). Tests run offline on fixtures.

## Layout

- `backend/`: Python backend (FastAPI, uv project: `pyproject.toml`, `.venv`). Package `cinesense/`, one folder per role; `tests/` mirrors the folders.
  - `core/`: films, search criteria, mood worlds, tag relevance, settings (no I/O)
  - `data_sources/`: adapters to Postgres (+ offline fixture), streaming, live search, Wikidata, Wikipedia, embeddings, YouTube
  - `search/`: deterministic ranking and widening; `taste/`: 👍/👎 profile
  - `catalog_import/`: offline catalogue build
  - `chat_agent/`: LangGraph agent (tools write the shared criteria; guard on input, grounding check on replies)
  - `web_api/`: HTTP layer; `deps.py` wires the adapters
  - `evaluation/`: scenarios, checks, judge, baselines
  - Layers only import downwards; `tests/test_architecture.py` enforces the allowed map.
- `frontend/`: Next.js (App Router, TypeScript, Tailwind, Vitest)
- `database/`: `schema.sql` and the local Supabase (`database/supabase/`)
- `evaluation/`: `scenarios.json`, `results/`, `REPORT.md` (written by `make eval`)
- `docs/`: design and plans, briefs, presentation, `video/` (recording scripts)

## Commands

```bash
cd backend && uv sync                     # backend deps (Python commands run in backend/)
make dev-api                              # FastAPI on :8000 (auto-reload)
make dev-web                              # Next.js on :3000
make test                                 # backend + frontend tests
cd backend && uv run pytest tests/web_api/test_api.py::test_health -v   # single backend test
cd frontend && npx vitest run __tests__/TileRows.test.tsx  # single frontend test
make lint                                 # ruff + eslint
cd backend && uv run pytest -m db         # tests against the Supabase catalogue (excluded by default)
make db-init                              # create/upgrade the cinesense schema
MOVIELENS_DB_PATH=/home/ali/projects/turing/moviefinder/db/moviedoc.db make ingest  # resumable full ingest
cd backend && uv run --env-file ../.env python -m cinesense.catalog_import.billing  # cast billing from Wikipedia leads (resumable)
cd backend && uv run --env-file ../.env python -m cinesense.catalog_import.pipeline --no-films --no-plots --german-titles  # German titles from Wikidata
cd backend && uv run --env-file ../.env python -m cinesense.catalog_import.pipeline --no-films --no-plots --enrich-live    # Wikidata + plots for live imports
cd backend && uv run --env-file ../.env python -m cinesense.catalog_import.pipeline --no-films --no-plots --languages      # recheck original languages (~7 min)
cd backend && uv run --env-file ../.env python -m cinesense.catalog_import.posters   # posters from Wikipedia for films without one (~2 min)
```

## Services (`.env`, see `.env.example`)

- Supabase (Postgres + pgvector)
- OpenRouter (LLMs)
- LangSmith tracing (EU endpoint)
- Streaming Availability API (`STREAMING_AVAILABILITY_API_KEY`, base `https://api.movieofthenight.com/v4`, header `X-API-Key`)
- YouTube Data API (`YOUTUBE_API_KEY`, optional)
- Own local Supabase (`database/supabase/config.toml`, project `CineSense`, DB on port 55322, Studio 55323; `make up` / `make down`, which pass `--workdir database` to the Supabase CLI). The migration in `database/supabase/migrations/` is a symlink to `database/schema.sql`. All tables live in the `cinesense` schema (`search_path` is set in `cinesense.data_sources.db.connect`).

## Gotchas

- The Next.js 16 dev server (Turbopack) sometimes keeps serving a stale `globals.css`. If a CSS change doesn't show, stop the server, delete `frontend/.next` and restart.
- Routes use English world ids (`/world/suspense`, `/world/comedy`, …) from `backend/cinesense/core/worlds.py`.
