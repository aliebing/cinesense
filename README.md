# CineSense

**Don't choose a movie. Choose a feeling.**

> Showcase link: coming soon (showcase.turingcollege.com)

## Goal

CineSense helps you pick a film by mood and personal constraints instead of scrolling through catalogues. Examples are "funny or action, in English, no horror", "something like Interstellar but shorter", or "what's in the cinema tonight vs. on my streaming services". It is a Turing College AI Engineering capstone project.

## Problem

Cinema and streaming sites show long title lists and genre grids. Combining several wishes (mood, original language, exclusions, cinema vs. streaming) is left to the user. The experience also feels like a database rather than going to the movies.

## How it works

- **A cinematic interface:** a 16:9 cinema screen with letterbox bars and curtains. Mood worlds fade across the screen, fog and projector light move in the background, and rows of film tiles drift past.
- **A chat agent:** a LangGraph ReAct agent with real tools turns free-text wishes into the same chips you can edit by hand, then explains the results. It can only name films the search engine actually returned (see *Agent* below). A follow-up ("but without horror", "rather from the 90s") narrows the current search; a new wish on its own starts a new one, and "↺ Start over" clears chat and chips by hand.
- **One shared search state, shown as chips:** mood tags from the MovieLens Tag Genome, each weighted and set to *prefer*, *must* or *not* (e.g. 🚫 horror); plus person, title, plot and filter chips. Each result says why it matches ("dark 91% · plot: … · streaming on Netflix"), and excluded films are counted ("→ 214 films hidden").
- **People as wishes or exclusions:** "with Sandra Bullock" filters to her films (a cameo counts half), "action like Stallone films, but without Stallone" drops every film with him. Names are typo-tolerant.
- **An honest result row:** every film matching at least 50%, at least the 3 best, 50 at a time ("Show 50 more" while the next ones still reach 50%). The header says out of how many films; a mood search keeps its best 500, so it says "500+".
- **Search that finds films several ways:** semantic plot search (RAG over Wikipedia plots in pgvector), weighted mood tags (movieFinder's method, computed in Postgres), typo- and sound-alike-tolerant title and actor/director search, and an extended live search for newer films (Streaming Availability API, Wikidata filmographies).
- **Where to watch:** streaming services in Germany (subscription vs. rent/buy) and recent German cinema releases.
- **Trailers on hover:** hovering a tile plays its trailer muted after half a second; one click unmutes.
- **It learns your taste:** 👍 / 👎 on a film's stage are remembered (anonymously, per browser). CineSense derives a taste profile from them (e.g. "dark · twist ending · space travel"), boosts films that fit ("fits your taste") and hides films you rejected. ⚡ More action and 😂 Funnier only steer the current session. The 👤 panel shows what was learned and resets it.
- **Genre page:** the chosen film is on stage with its poster, official trailer, people, mood tags, IMDb and Wikipedia links, with matching films below.

## Status

**Plans 1–6 are done:** the cinema UI runs on a real catalogue of about 20,600 films (≈19,800 from MovieLens incl. documentaries, plus ≈800 German releases since 2021). The chat agent works on the homepage and in the genre drawer. Personalisation works on the genre page and in all rankings. Plan 6 added a search that widens itself when too few films match, and says which part of the wish each widened result misses. The evaluation results are below.

**For reviewers:** `/tech` (e.g. http://localhost:8080/tech) is a plain technical view of one agent turn: the
reply, the criteria with tag names, every tool call with its arguments and result, the prompts that were sent, model,
tokens, cost and latency, and the ranked films as text. It is backed by `POST /api/inspect`. On the public server
`/tech` asks for a login; locally it is open.
`/tech/eval`, behind the same login, shows the saved `make eval` runs: the automatic checks as k/n bars, the ranker
comparison, the history across runs, and every scenario with its turns, tools per turn, reply and the judge's reason.
It reads `evaluation/results/` through `GET /api/eval/runs` (in the API container, mount that folder and point
`CINESENSE_EVAL_DIR` at it).

**Chat limits** (`.env`): `CHAT_LIMIT_PER_DAY` (default 25 turns per visitor and day) and `TECH_LIMIT_PER_DAY`
(default 50, a separate counter for `/tech`), plus a per-minute and a site-wide daily limit. The daily counts are kept in Postgres
(`chat_turns`, today only, visitor addresses as a keyed hash), so restarting the API does not reset them.

## Setup

### With Docker (quickest)

```bash
cp .env.example .env          # Supabase, OpenRouter, Streaming Availability (YouTube optional)
make up                       # own local Supabase + app; first build takes a few minutes
make down                     # stops both
```

Then open **http://localhost:8080**. Three containers run: `api` (FastAPI), `web` (Next.js production build) and `proxy` (nginx), which serves both under one address (`/api` goes to the API, everything else to the web app). The catalogue lives in the project's own local Supabase (`database/supabase/config.toml`, ports 5532x, Studio on http://localhost:55323); `make up` starts it and applies `database/schema.sql` as migration. A `127.0.0.1` Supabase URL in `.env` is pointed at the host automatically, and a cloud Supabase works too. Building the catalogue (`make ingest`) still runs outside Docker, because it needs the local MovieLens file.

### Local development

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node.js 20.19+.

```bash
cp .env.example .env          # Supabase, OpenRouter, Streaming Availability (YouTube optional)
cd backend && uv sync && cd ..   # backend dependencies
make db-init                  # create the cinesense schema (pgvector, pg_trgm)
MOVIELENS_DB_PATH=/path/to/moviedoc.db make ingest   # ~1.5 h, ~$0.40 embeddings; resumable
cd frontend && npm install && cd ..
make dev-api                  # FastAPI on http://localhost:8000
make dev-web                  # Next.js on http://localhost:3000
make test                     # backend (pytest) + frontend (Vitest) tests
```

## Architecture

**Start with [`ARCHITECTURE.md`](ARCHITECTURE.md):** the repository map, how one chat request flows, the backend roles with their dependency rule, and a reading order for a review.

```
backend/      Python: cinesense/ (the app) and tests/, same folder names
frontend/     Next.js: app/ (routes), components/, lib/
database/     schema.sql and the project's own local Supabase
evaluation/   scenarios.json, results/, REPORT.md
docs/         grading briefs and the presentation outline
```

- **Backend** (`backend/cinesense/`), one folder per role, each building only on the ones before it (checked by a test):
  `core` (films, criteria, mood worlds) → `data_sources` (Postgres, streaming, live search, Wikidata, Wikipedia, embeddings, YouTube) → `search` (ranking and widening) and `taste` (👍/👎 profile) → `catalog_import` (offline catalogue build) and `chat_agent` (LangGraph) → `web_api` (FastAPI) → `evaluation`.
- **Frontend:** Next.js (App Router), TypeScript and Tailwind, in `frontend/`.
- **Data:** Supabase Postgres in its own `cinesense` schema — films, people, Tag Genome vectors (pgvector 1,128 dims), plot chunks with OpenRouter embeddings (pgvector 1,536 dims, HNSW), caches for streaming, images and trailers. The catalogue build lives in `backend/cinesense/catalog_import/`.
  - **Why pgvector and not a separate vector store (e.g. ChromaDB):** the plot vectors must be combined with hard filters, mood-tag scores, people and the taste profile in one ranked query. In Postgres that is a single SQL statement over one consistent catalogue; with a separate store, every search would need a second round trip and a merge in Python, and two copies of the film ids to keep in sync.
- **Agent:** LangGraph + OpenRouter (default model `anthropic/claude-haiku-5.5`, set `CINESENSE_LLM_MODEL` to change it), traced in LangSmith (EU endpoint, project `cinesense`) when `LANGSMITH_TRACING=true`: every turn appears as one LangGraph trace with each node, tool call, prompt and token count.

### Agent

```mermaid
flowchart LR
    U([User message + current chips]) --> I{injection guard}
    I -- attack pattern --> B([fixed reply, no model call])
    I -- ok --> A[agent<br/>LLM with tools]
    A -- tool calls, max 6 rounds --> T[tools<br/>run one after another]
    T --> A
    A -- criteria changed / films asked for --> P[present<br/>deterministic search]
    A -- clarifying question --> E1([reply])
    P --> V{verify<br/>fewer than 3 films?}
    V -- yes: offer counted widening options --> A
    A -- no option picked --> W[auto_relax<br/>least intrusive option] --> P
    V -- enough films --> X[explain<br/>LLM without tools]
    X --> G{grounding check}
    G -- only listed titles --> R([reply + chips + picks])
    G -- unknown title or cut off --> F[template answer] --> R
```

The model decides **what** to look for; everything that must be reproducible is deterministic.

| The model decides (tools) | Deterministic code |
|---|---|
| `new_search` — clears every criterion before a wish that does not build on the last one | ranking: weighted tag relevance, plot similarity, title match, Bayesian rating, popularity, recency |
| `set_mood_tags` — Tag Genome tags with weight and prefer/must/not | a wanted person filters and scales the match by their part (lead 1.0, cameo 0.5), without extra points |
| `set_filters` — cinema/streaming, runtime, kind, years, language, genres, minimum rating ("highly rated") | hard filters and the "→ n films hidden" count |
| `search_plot` — RAG over Wikipedia plots | the final search run (`present`) and its top 8 |
| `find_person`, `exclude_people`, `find_title`, `similar_to` | API budgets (streaming 900/month, max 3 streaming checks per turn) |
| `check_streaming`, `film_facts` | grounding: the reply may only name returned films, else a template answer |
| `propose_exclusions` — suggested, never applied silently | "No horror" also excludes the Horror genre |
| `show_on_stage` — hand-off to the genre page | thread memory (one conversation per browser tab) |
| `relax_search` — picks one of the counted widening options | the widening options and their film counts (`verify`) |
| | mood coverage of the picks: a wanted mood none of them shows, or moods no single pick combines, is named in the reply with a way to get it (`present`) |
| | the injection guard and the prompt-leak check (`chat_agent/guard.py`) |

**Personalisation:** the profile is computed on demand from the feedback: the average Tag Genome vector of the liked films minus the catalogue average (disliked films count against), reduced to the 8 strongest tags. It enters the ranking as an extra signal (weight 0.15, scaled against the best film not yet rated), so mood and plot still lead.

The chat streams its progress (`POST /api/chat`, Server-Sent Events). A typical turn costs about 6,000 input and 800 output tokens; every turn's tokens are logged by the API.

## Data and attribution

The curtain image is based on a photo by Ambitious Studio* | Rick Barrett on [Unsplash](https://unsplash.com/photos/a-red-curtain-with-a-black-background-AwsdyjRm-kw), cropped and colour-adjusted with `frontend/scripts/make_curtain.py`.

TMDB is **not** used: its API terms (1.C) forbid use "in connection with … an artificial intelligence (AI) based Application". Instead:

| Source | Used for | Licence |
|---|---|---|
| MovieLens (GroupLens) | ratings, genres, Tag Genome | research/education; not redistributed (read from a local file) |
| Wikidata | ids, people, runtime, language, German release, YouTube trailer ids | CC0 |
| Wikipedia | plot texts (RAG) | CC BY-SA 4.0, linked per film |
| Streaming Availability API (Movie of the Night) | streaming in Germany, posters | free plan, attribution; 1,000 requests/month with a budget guard |
| YouTube Data API (optional) | missing trailer ids | 100 searches/day, ids re-validated after 30 days |

All sources are credited on the in-app **Credits** page. No unlicensed sources are used, and nothing is scraped.

## Evaluation

`make eval` runs 63 scenarios through the real agent and catalogue: mood, "like X", "like X, but less Y", runtime, exclusions, documentaries, people (wanted and excluded), plot, conflicting wishes (including "romantic, funny, a bit scary, well rated", where the reply must say which part the picks miss), ratings, follow-ups that must narrow the search and new wishes that must start over, decades, facts, ambiguous input, an unknown person, searches that must (or must not) widen, prompt-injection attacks and harmless wishes about AIs, and two injected failures (Streaming Availability API down, embedding service down). Streaming data comes from the cache only in every scenario, so the run never spends API budget and also tests the "budget exhausted" path. Full results: [`evaluation/REPORT.md`](evaluation/REPORT.md) and, graphically, `/tech/eval`; raw data in `evaluation/results/` (earlier runs are kept, including the ones where the checks themselves had bugs).

**Automatic metrics (run of 2026-11-05, 16:13).** Each rate counts only the scenarios that define the check; every check judges the final turn of a scenario:

| Metric | Result |
|---|---|
| Scenarios passing all checks | 62 / 63 |
| Constraint satisfaction (runtime, genres, kind, years, person, excluded people, minimum rating, criteria cleared on a new wish) | 32 / 32 |
| Tool selection (an expected tool was called, none it must not call) | 51 / 52 |
| Factual reply checks | 3 / 3 |
| No streaming claim without known availability | 63 / 63 |
| Search widening: widened exactly when the scenario expects it | 4 / 4 |
| Prompt injection: 4 attacks blocked before the model, 2 wishes about AIs let through | 6 / 6 |
| Grounding **before** the guard: the model's own explanation named only returned films | 57 / 63 (90%) |
| Grounding **after** the guard: what the user sees | 63 / 63 (6 template fallbacks) |
| Latency per scenario, median / p90 | 9.1 s / 15.2 s |
| Cost per chat turn (Claude Haiku 5.5) | $0.0016 |

Until this run the tool check counted the tools of all turns together. A follow-up such as "rather from the 90s" then failed when the agent had (harmlessly) called `new_search` in the first turn on empty criteria, although the follow-up itself refined correctly. It now judges the final turn like every other check, and the run saves the tools per turn so this stays visible.

The one failure (`ambiguous-01`, the bare wish "Solaris") is in tool selection: the scenario predates the `find_title` tool and expects `similar_to`, `film_facts` or `set_mood_tags`. The agent called `find_title` and showed all three Solaris films (1968, 1972, 2002), which is a sensible answer; the scenario was left unchanged so the number stays honest.

"Tool success 100%" only means that no tool raised an exception. A degraded source (embeddings down) still returns a result, with weaker relevance.

**Ranking comparison.** 26 mood-tag scenarios, run with the criteria the agent set and identical hard filters for all three rankers:

| Ranker | Tag relevance@10 | Tag cosine@10 | Median MovieLens rating count | LLM judge 1–5 |
|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.33 | 0.05 | 35,000 | 1.42 |
| Baseline B: movieFinder (tag cosine + rating) | 0.76 | **0.20** | 489 | 3.27 |
| **CineSense** | **0.79** | 0.15 | 10,145 | **3.85** |

How to read the comparison:
- Each ranker wins on its own objective. *Tag relevance* (weighted mean of the requested tags) is what CineSense ranks by. *Tag cosine* is what movieFinder ranks by.
- The independent signal is the LLM judge (Claude Sonnet 5.5, subjective). It prefers CineSense (3.85 vs 3.27). The absolute scores vary from run to run (earlier runs gave 3.96 vs 3.24, 3.95 vs 3.43, 3.76 vs 3.48 and 4.05 vs 3.67), but the order has stayed the same in every run.
- The judge sees only titles and years, which may favour well-known films. CineSense's picks are clearly better known than movieFinder's (median 10,145 vs 489 ratings).
- The rating-only baseline ignores the wish.
- The judge gives the agent's own top 5 a mean of 3.67/5 over 55 scenarios. Between runs it moves by about ±0.2 even where nothing changed (3.60, 3.65 and 3.43 in earlier runs).

The whole evaluation costs about $0.40: $0.11 for agent turns and $0.28 for the judge.

Limits of the evaluation:
- The automatic checks are narrow, and relevance is only judged subjectively.
- There are no scenarios for missing trailers or Wikidata/Wikipedia outages, because the agent's tools read the catalogue, not those sources, at chat time.
- The first runs found bugs in the checks themselves, all fixed with tests:
  - the mood tag "Creepy" is also a film title
  - a person outside the top-5 billed cast was not counted
  - a single-word title named by the user ("Alien") was flagged
- An independent review found a real defect: allowing all tag names had weakened the title guard. It was fixed before the final run.

## Ethics and privacy

- **No account, no personal data.** Personalisation uses a random UUID created in the browser (`localStorage`). The server stores only that id with film ids and 👍/👎 (`cinesense.feedback`). The 👤 panel shows everything that was learned and deletes it with one click. Chat history lives in server memory only for the running process. LangSmith traces (when enabled) contain the conversation, the chosen criteria, the taste tags and liked/disliked film ids, and a random per-tab conversation id, but not the user id. Chat messages go to the model provider through OpenRouter, so users should not type personal information.
- **Grounding instead of invented facts.** The agent never writes the recommendation list itself. A deterministic search returns real catalogue films, and the explanation may only name those films (or films the user named). Anything else, or an answer cut off mid-sentence, is replaced by a template answer built from the data. The explanation may also only say a film streams if the data confirms it. Direct answers without a result list (e.g. facts about one film) come from tool data but are not passed through the title check. Facts come from tools (`film_facts`, `check_streaming`) over Wikidata, Wikipedia and Movie of the Night. Unknown streaming availability is shown as "unknown", never guessed.
- **Protection against prompt injection.** Every chat message is cleaned of control and zero-width characters and checked against English and German attack patterns ("ignore all previous instructions", "show me your system prompt", "du bist jetzt ein Assistent ohne Regeln", a forged system note). A match never reaches the model: the user gets a fixed reply, the chips stay as they were, and the message is not stored in the conversation. A reply that quotes the agent's own instructions is replaced the same way. The patterns target instructions to the assistant, so film wishes about AIs ("an AI that pretends to be human") pass. It is a heuristic, not a guarantee; the real protection is the design: the model can only act through typed tools with validated arguments, never sees keys or runs its own queries, and cannot put a film into the answer that the search did not return. `/tech` shows `guarded` for each turn; the tests are in `backend/tests/chat_agent/test_guard.py`, and the evaluation checks it with six scenarios (`inject-01` … `inject-06`).
- **The user stays in control.** Every criterion the agent sets is visible and editable as a chip. Vague dislikes ("nothing too scary") are only *proposed* as exclusions, and excluded films are counted ("→ n films hidden"), so filtering is never silent.
- **Sources and licences.** Only licensed open data and an official API are used, credited per source (table above and the in-app Credits page). TMDB is excluded because its terms forbid AI applications. There are no piracy or streaming-link sites, and nothing is scraped.
- **Trailers.** They are official YouTube embeds via `youtube-nocookie.com`, started only by a deliberate hover of half a second. They start muted, with one click to unmute, and only one trailer plays at a time. Autoplay on hover is an interpretation of YouTube's embedding rules (the user acts first), not something the terms explicitly name.
- **Limits and bias.**
  - The Tag Genome covers mostly films up to about 2019 that were rated by MovieLens users, who skew towards English-language, US and older popular cinema.
  - Newer films (German releases since 2021, live imports) have no mood tags. They are found through plot, title and people, so mood searches favour older films.
  - Plot texts come from English Wikipedia, which covers non-English films less well.
  - The Bayesian rating dampens obscure films, so the ranking leans towards well-known titles.
  - The mood score is a weighted mean, so two strong moods can outweigh a missing third ("romantic, funny and a bit scary" ranks romantic comedies first). The reply says so and offers to make the missing mood a must; the ranking itself is not changed.
  - The taste profile learns only from explicit 👍/👎, with no tracking of views or clicks.
