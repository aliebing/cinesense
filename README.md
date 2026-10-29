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
- **One shared search state, shown as chips:** mood tags from the MovieLens Tag Genome, each weighted and set to *prefer*, *must* or *not* (e.g. 🚫 horror); plus person, title, plot and filter chips. Each result says why it matches ("dark 91% · plot: … · streaming on Netflix"), and excluded films are counted ("→ 214 films hidden").
- **Search that finds films several ways:** semantic plot search (RAG over Wikipedia plots in pgvector), weighted mood tags (movieFinder's method, computed in Postgres), typo- and sound-alike-tolerant title and actor/director search, and an extended live search for newer films (Streaming Availability API, Wikidata filmographies).
- **Where to watch:** streaming services in Germany (subscription vs. rent/buy) and recent German cinema releases.
- **Trailers on hover:** hovering a tile plays its trailer muted after half a second; one click unmutes.
- **Genre page:** the chosen film is on stage with its poster, official trailer, people, mood tags, IMDb and Wikipedia links, with matching films below.

## Status

**Plans 1–2 are done:** the cinema UI runs on a real catalogue of about 20,600 films (≈19,800 from MovieLens incl. documentaries, plus ≈800 German releases since 2021). The chat agent (Plan 3), personalisation (Plan 4) and the evaluation (Plan 5) follow; see `docs/superpowers/plans/2026-10-29-cinesense-roadmap.md`.

## Setup

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node.js 20.19+.

```bash
cp .env.example .env          # Supabase, OpenRouter, Streaming Availability (YouTube optional)
uv sync                       # backend dependencies
make db-init                  # create the cinesense schema (pgvector, pg_trgm)
MOVIELENS_DB_PATH=/path/to/moviedoc.db make ingest   # ~1.5 h, ~$0.40 embeddings; resumable
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
- **Data:** Supabase Postgres in its own `cinesense` schema — films, people, Tag Genome vectors (pgvector 1,128 dims), plot chunks with OpenRouter embeddings (pgvector 1,536 dims, HNSW), caches for streaming, images and trailers. The ingest lives in `src/cinesense/ingest/`.
- **Planned:** LangGraph + OpenRouter for the agent, LangSmith for tracing.

The full design is in `docs/superpowers/specs/2026-10-29-cinesense-design.md`.

## Data and attribution

The curtain image is based on a photo by Ambitious Studio* | Rick Barrett on [Unsplash](https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw), cropped and colour-adjusted with `scripts/make_curtain.py`.

TMDB is **not** used: its API terms (1.C) forbid use "in connection with … an artificial intelligence (AI) based Application". Instead:

| Source | Used for | Licence |
|---|---|---|
| MovieLens (GroupLens) | ratings, genres, Tag Genome | research/education; not redistributed (read from a local file) |
| Wikidata | ids, people, runtime, language, German release, YouTube trailer ids | CC0 |
| Wikipedia | plot texts (RAG) | CC BY-SA 4.0, linked per film |
| Streaming Availability API (Movie of the Night) | streaming in Germany, posters | free plan, attribution; 1,000 requests/month with a budget guard |
| YouTube Data API (optional) | missing trailer ids | 100 searches/day, ids re-validated after 30 days |

All sources are credited on the in-app **Credits** page. No unlicensed sources are used, and nothing is scraped.

## Ethics and privacy

To be completed in Plan 5. It will cover the anonymous user id with no personal data, grounding (no invented film facts), source attribution, and the limits and bias of the recommendations.
