# CineSense

**Don't choose a movie. Choose a feeling.**

> Showcase link: coming soon (showcase.turingcollege.com)

## Goal

CineSense helps you pick a film by mood and personal constraints instead of scrolling through catalogues. Examples are "funny or action, in English, no horror", "something like Interstellar but shorter", or "what's in the cinema tonight vs. on my streaming services". It is a Turing College AI Engineering capstone project.

## Problem

Cinema and streaming sites show long title lists and genre grids. Combining several wishes (mood, original language, exclusions, cinema vs. streaming) is left to the user. The experience also feels like a database rather than going to the movies.

## How it works

- **A cinematic interface:** a 16:9 cinema screen with letterbox bars and curtains. Mood worlds fade across the screen, fog and projector light move in the background, and rows of film tiles drift past.
- **A chat agent (planned, Plan 3):** a LangGraph agent with real tools turns free-text wishes into structured preferences. It looks up **real** film data from TMDB and explains why each suggestion fits.
- **Recommendations:** hard filters, semantic similarity, Bayesian-weighted TMDB ratings and your own 👍/👎 feedback are combined into a match percentage. Semantic similarity and feedback come with Plans 2–4.
- **Genre page:** the chosen film is on stage with its poster, official trailer and reasons, with matching films below.

## Status

**Plan 1 is done: the UI runs on placeholder data.** All films are fictional "Demo-Film" entries, marked "Platzhalter", with stock photos. Real TMDB data, the agent and personalisation follow in Plans 2–4; see `docs/superpowers/plans/2026-10-29-cinesense-roadmap.md`.

## Setup

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node.js 20.19+.

```bash
cp .env.example .env          # fill in keys (not needed for Plan 1)
uv sync                       # backend dependencies
cd web && npm install && cd ..
make dev-api                  # FastAPI on http://localhost:8000
make dev-web                  # Next.js on http://localhost:3000
make test                     # backend (pytest) + frontend (Vitest) tests
```

## Architecture

- **Backend:** Python, FastAPI and Pydantic, in `src/cinesense/`.
  - `domain`: the models and the six mood worlds
  - `providers`: data sources behind one interface (placeholder fixtures now, TMDB next)
  - `recommend`: deterministic filters and the baseline ranking
  - `api`: the HTTP layer
- **Frontend:** Next.js (App Router), TypeScript and Tailwind, in `web/`.
- **Planned:** LangGraph + OpenRouter for the agent, Supabase (Postgres + pgvector) for the catalogue and embeddings, LangSmith for tracing.

The full design is in `docs/superpowers/specs/2026-10-29-cinesense-design.md`.

## Data and attribution

The curtain image is based on a photo by Ambitious Studio* | Rick Barrett on [Unsplash](https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw), cropped and colour-adjusted with `scripts/make_curtain.py`.

Film data will come from [TMDB](https://www.themoviedb.org/), and streaming availability from JustWatch via TMDB. Both will be attributed in the app once integrated (Plan 2). No unlicensed sources are used, and nothing is scraped.

## Ethics and privacy

To be completed in Plan 5. It will cover the anonymous user id with no personal data, grounding (no invented film facts), source attribution, and the limits and bias of the recommendations.
