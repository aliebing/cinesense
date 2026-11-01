# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CineSense ("Don't choose a movie. Choose a feeling.") is a Turing College AI Engineering capstone: mood-based movie discovery with a cinematic, animated UI and a LangGraph chat agent grounded in real catalogue data (MovieLens, Wikidata, Wikipedia).

The approved design is in `docs/superpowers/specs/2026-10-29-cinesense-design.md`. Read it before changing behaviour or look. Implementation plans and the 4-week roadmap are in `docs/superpowers/plans/`. Approved mockups are in `docs/superpowers/specs/mockups/`.

The grading briefs are `turing-college-capstone.md` and `turing-college-sprint4.md`.

## Conventions

- **Language:** UI text, code, identifiers, comments, commits and docs are all English. Talk to the user in German.
- **Look:** dark only, on a matte near-black ground, with fog and light on every page. The main stage is a wide (~2.25:1) cinema screen with letterbox bars and solid red side curtains; tune via the CSS variables at the top of `web/app/globals.css`. Text must stay readable over all effects.
- **Data:** never fabricate film facts. **No TMDB** (its terms forbid AI apps). Sources: MovieLens (local file, never commit it), Wikidata, Wikipedia, Streaming Availability API (1,000 req/month — every call goes through the cache/budget guard), optional YouTube Data API (95 searches/day).
- **External services** stay behind adapters (`src/cinesense/providers/`). Tests run offline on fixtures.

## Layout

- `src/cinesense/`: Python backend (FastAPI)
  - `domain/`: models and the six mood worlds
  - `providers/`: data sources
  - `recommend/`, `search/`: filtering and ranking (deterministic)
  - `agent/`: LangGraph chat agent (tools write the shared criteria; grounding check on replies)
  - `ingest/`: catalogue build
  - `api/`: HTTP layer
- `tests/`: pytest
- `web/`: Next.js frontend (App Router, TypeScript, Tailwind, Vitest)

## Commands

```bash
uv sync                                   # backend deps
make dev-api                              # FastAPI on :8000 (auto-reload)
make dev-web                              # Next.js on :3000
make test                                 # backend + frontend tests
uv run pytest tests/test_api.py::test_health -v   # single backend test
cd web && npx vitest run __tests__/TileRows.test.tsx  # single frontend test
make lint                                 # ruff + eslint
uv run pytest -m db                       # tests against the Supabase catalogue (excluded by default)
make db-init                              # create/upgrade the cinesense schema
MOVIELENS_DB_PATH=/home/ali/projects/turing/moviefinder/db/moviedoc.db make ingest  # resumable full ingest
uv run --env-file .env python -m cinesense.ingest.billing  # cast billing from Wikipedia leads (resumable)
uv run --env-file .env python -m cinesense.ingest.pipeline --no-films --no-plots --german-titles  # German titles from Wikidata
uv run --env-file .env python -m cinesense.ingest.pipeline --no-films --no-plots --enrich-live    # Wikidata + plots for live imports
```

## Services (`.env`, see `.env.example`)

- Supabase (Postgres + pgvector)
- OpenRouter (LLMs)
- LangSmith tracing (EU endpoint)
- Streaming Availability API (`STREAMING_AVAILABILITY_API_KEY`, base `https://api.movieofthenight.com/v4`, header `X-API-Key`)
- YouTube Data API (`YOUTUBE_API_KEY`, optional)
- The Supabase DB is shared with other projects: all CineSense tables live in the `cinesense` schema (`search_path` is set in `cinesense.db.connect`).

## Gotchas

- The Next.js 16 dev server (Turbopack) sometimes keeps serving a stale `globals.css`. If a CSS change doesn't show, stop the server, delete `web/.next` and restart.
- Routes use English world ids (`/world/suspense`, `/world/comedy`, …) from `src/cinesense/domain/worlds.py`.
