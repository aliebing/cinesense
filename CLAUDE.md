# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CineSense ("Don't choose a movie. Choose a feeling.") is a Turing College AI Engineering capstone: mood-based movie discovery with a cinematic, animated UI and a LangGraph chat agent grounded in real TMDB data.

The approved design is in `docs/superpowers/specs/2026-10-29-cinesense-design.md`. Read it before changing behaviour or look. Implementation plans and the 4-week roadmap are in `docs/superpowers/plans/`. Approved mockups are in `docs/superpowers/specs/mockups/`.

The grading briefs are `turing-college-capstone.md` and `turing-college-sprint4.md`.

## Conventions

- **Language:** UI text is German. Code, identifiers, comments, commits and docs are English. Talk to the user in German.
- **Look:** dark only, on a matte near-black ground, with fog and light on every page. The main stage is a 16:9 cinema frame with letterbox bars and curtain hints. Text must stay readable over all effects.
- **Data:** never fabricate film facts. Plan 1 uses clearly labelled fictional "Demo-Film" placeholders. Real data comes only from TMDB, and no unlicensed sources are allowed.
- **External services** stay behind adapters (`src/cinesense/providers/`). Tests run offline on fixtures.

## Layout

- `src/cinesense/`: Python backend (FastAPI)
  - `domain/`: models and the six mood worlds
  - `providers/`: data sources
  - `recommend/`: filtering and ranking
  - `api/`: HTTP layer
- `tests/`: pytest
- `web/`: Next.js frontend (App Router, TypeScript, Tailwind, Vitest)

## Commands

```bash
uv sync                                   # backend deps
make dev-api                              # FastAPI on :8000
make dev-web                              # Next.js on :3000
make test                                 # backend + frontend tests
uv run pytest tests/test_api.py::test_health -v   # single backend test
cd web && npx vitest run __tests__/TileRows.test.tsx  # single frontend test
make lint                                 # ruff + eslint
```

## Services (`.env`, see `.env.example`)

- Supabase (Postgres + pgvector)
- OpenRouter (LLMs)
- LangSmith tracing (EU endpoint)
- TMDB (`TMDB_API_KEY`, `TMDB_READ_ACCESS_TOKEN`)
