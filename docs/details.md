# CineSense – details

The [README](../README.md) gives the overview. This page keeps the full text: every feature, the admin area and limits, the agent's tools, the whole evaluation and the ethics notes.

## All features

- **A cinematic interface:** a 16:9 cinema screen with letterbox bars and curtains. Seven mood worlds fade across the screen (Drama & Life joined the six of the design for pure dramas and war films; every feature film has a world, its main one by its mood tags), fog and projector light move in the background, and two rows per world drift past: its newest top-rated films of the last eight years and its top classics. A film opened from there shows its genre and 29 films like it; opened from the search, it keeps the search's mood settings and films.
- **A chat agent:** a LangGraph ReAct agent with real tools turns free-text wishes into the same chips you can edit by hand, then explains the results. It can only name films the search engine actually returned (see *The agent in detail* below). A follow-up ("but without horror", "rather from the 90s") narrows the current search; a new wish on its own starts a new one, and "↺ Start over" clears chat and chips by hand.
- **One shared search state, shown as chips:** mood tags from the MovieLens Tag Genome, each weighted and set to *prefer*, *must* or *not* (e.g. 🚫 horror); plus person, title, plot and filter chips. Each result says why it matches ("dark 91% · plot: … · streaming on Netflix"), and excluded films are counted ("→ 214 films hidden").
- **People as wishes or exclusions:** "with Sandra Bullock" filters to her films (a cameo counts half), "action like Stallone films, but without Stallone" drops every film with him. Names are typo-tolerant.
- **An honest result row:** the best matches in front (up to 6 from 70%, at least 3), below them a running row with every further film from 60%, 30 at a time with « » arrows (from 70% or higher when more than 500 films reach 60%, from 50% when fewer than 28 do). The header says out of how many films; a mood search keeps its best 500, so it says "500+".
- **Search that finds films several ways:** semantic plot search (RAG over Wikipedia plots in pgvector), weighted mood tags (movieFinder's method, computed in Postgres), typo- and sound-alike-tolerant title and actor/director search, and an extended live search for newer films (Streaming Availability API, Wikidata filmographies).
- **Where to watch:** streaming services in Germany (subscription vs. rent/buy) and recent German cinema releases.
- **Trailers on hover:** hovering a tile plays its trailer muted after half a second; one click unmutes.
- **It learns your taste:** 👍 / 👎 on a film's stage are remembered (anonymously, per browser). CineSense derives a taste profile from them (e.g. "dark · twist ending · space travel"), boosts films that fit ("fits your taste") and hides films you rejected. ⚡ More action and 😂 Funnier only steer the current session. The 👤 panel shows what was learned and resets it.
- **Genre page:** the chosen film is on stage with its poster, official trailer, people, mood tags, IMDb and Wikipedia links, with matching films below.

## Status

**Plans 1–6 are done:** the cinema UI runs on a real catalogue of about 20,600 films (≈19,800 from MovieLens incl. documentaries, plus ≈800 German releases since 2021). The chat agent works on the homepage and in the genre drawer. Personalisation works on the genre page and in all rankings. Plan 6 added a search that widens itself when too few films match, and says which part of the wish each widened result misses. The evaluation results are below.

**For reviewers:** `/admin` (e.g. http://localhost:8080/admin) is the operator's area, with three pages in one
navigation. On the public server it asks for a login (`TECH_USER` / `TECH_PASSWORD_HASH`, a bcrypt hash from `make admin-password`, checked by the frontend and again
by every API behind it); locally it is open. The old addresses `/tech` and `/tech/eval` redirect here.

- **Tech** (`/admin/tech`): a plain technical view of one agent turn: the reply, the criteria with tag names, every
  tool call with its arguments and result, the prompts that were sent, model, tokens, cost and latency, and the ranked
  films as text. Backed by `POST /api/inspect`.
- **Visitors** (`/admin/visitors`): every assistant turn of the last 30 days, newest first, with message, number of
  films, tools, tokens, cost and duration, and the selected turn in full (the conversation before it, reply,
  understood search, films, tool calls, template fallback). The API writes one row per turn into `chat_log` and
  deletes rows older than 30 days on every write; visitor and conversation are keyed hashes, never addresses
  (`web_api/chat_log.py`, `GET /api/admin/visitors`). The privacy notice says so.
- **Evaluation** (`/admin/evaluation`): start a run from the browser. Choose the agent model (Claude Haiku 5.5,
  Claude Sonnet 5.5, GPT-5.6 Luna, GPT-5.6 Terra) with its token prices, read live from OpenRouter, and a selection of
  scenarios (6 for a quick demo, 15, all 63, or your own). The page estimates the cost from the last full run's tokens,
  then shows the run live: the scenario being asked, and each result with its checks, reply, films and judge score as
  soon as it is in. The judge stays Claude Sonnet 5.5, so scores compare across runs. One run at a time; it can be
  stopped after the current scenario. Below: the last 10 runs (`make eval` and the ones started here), and the selected
  run in full: the automatic checks as k/n bars, the ranker comparison, the history of full runs, and every scenario
  with its turns, tools per turn, reply and the judge's reason. Runs started here are saved to
  `CINESENSE_EVAL_RUNS_DIR`; the `make eval` runs are read from `CINESENSE_EVAL_DIR` (`web_api/eval_view.py`,
  `evaluation/session.py`).

**Chat limits** (`.env`): `CHAT_LIMIT_PER_DAY` (default 25 turns per visitor and day) and `TECH_LIMIT_PER_DAY`
(default 50, a separate counter for `/admin/tech`), plus a per-minute and a site-wide daily limit. The daily counts are kept in Postgres
(`chat_turns`, today only, visitor addresses as a keyed hash), so restarting the API does not reset them.

## The agent in detail

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
| `find` (a title or a person), `similar_to`; people to exclude are a `set_filters` field | API budgets (streaming 900/month, max 3 streaming checks per turn) |
| `film_info` (facts, and with `streaming` where it streams) | grounding: the reply may only name returned films, else a template answer |
| `propose_exclusions` — suggested, never applied silently | "No horror" also excludes the Horror genre |
| `show_on_stage` — hand-off to the genre page | thread memory (one conversation per browser tab) |
| `relax_search` — picks one of the counted widening options | the widening options and their film counts (`verify`) |
| | mood coverage of the picks: a wanted mood none of them shows, or moods no single pick combines, is named in the reply with a way to get it (`present`) |
| | the injection guard and the prompt-leak check (`chat_agent/guard.py`) |

**Personalisation:** the profile is computed on demand from the feedback: the average Tag Genome vector of the liked films minus the catalogue average (disliked films count against), reduced to the 8 strongest tags. It enters the ranking as an extra signal (weight 0.15, scaled against the best film not yet rated), so mood and plot still lead.

The chat streams its progress (`POST /api/chat`, Server-Sent Events). A typical turn costs about 6,000 input and 800 output tokens; every turn's tokens are logged by the API.

## How the search decides

Filters have no weight: they keep a film or drop it. Only the ranking signals are weighted. One search runs in four steps (`search/service.py`, `search/ranking.py`, `search/widening.py`).

**1. Candidates: which films are considered at all.**

| The wish has | Candidates |
|---|---|
| a told story (plot) | the 150 best plot matches; mood tags only rank them |
| only mood tags | the 500 films with the highest weighted tag relevance in the whole catalogue |
| a person or a title | their films; mood tags only rank them |

**2. Hard filters: in or out, no weight.** Everything from `set_filters` and the advanced search (years, runtime, original language, cinema or streaming, services, minimum rating, film or documentary, mood world), excluded genres and people, 👎 films, and two tag modes: a *not* tag drops films from a relevance of 0.5, a *must* tag keeps only films from 0.6. A film that fails one of them is gone, however well it fits otherwise.

**3. Ranking: the weighted part** (`WEIGHTS` in `search/ranking.py`).

| Signal | Weight | Value per film |
|---|---|---|
| mood tags (*prefer* and *must*) | 0.40 | Tag Genome relevance 0–1, absolute (a film that is only 30% funny is never a full match) |
| plot | 0.30 | plot fit 0–1, from the search's own noise floor up to the best match |
| title | 0.20 | title similarity 0–1 |
| taste profile | 0.15 | only with 👍/👎 |
| MovieLens rating (Bayesian) | 0.10 | always |
| popularity (rating count, log scale) | 0.08 | always |
| recency | 0.04 | always, a small bonus from 1970 to today |

Only the active signals count: the match is their weighted sum divided by the sum of their weights. A wanted person is not points but a factor (lead 1.0, smaller parts less), so a famous co-star cannot lift a film that misses the mood. The weight 1–10 of a single tag only shares the tag part among several tags; against the plot, the tags together always weigh 0.40.

*Example: a told story + "time loop" + "from 1995".* Five signals are active (0.92 in all): tags 43%, plot 33%, rating 11%, popularity 9%, recency 4%. "From 1995" has no share; it drops films. Without it, *Groundhog Day* (1993) leads with 95%, followed by *12:01* and *Donnie Darko*; with it, 111 of the 150 candidates remain and *Donnie Darko* (2001) leads with 72%. *Groundhog Day* is not ranked lower; it is gone, as a filter should do. The other films keep their percentages.

**4. Widening: only when fewer than 3 films remain.** The code lists what may be loosened, least intrusive first, and counts each option before offering it: a *must* tag becomes *prefer*; the mood is searched in the plots instead of the tags; runtime +30 min; years ±10; minimum rating −0.3 (or dropped); then language, mood world, streaming services, cinema or streaming. The model picks one (`relax_search`); if it picks none, the code takes the least intrusive option that finds enough films. The page says what was widened, and each widened film shows with ≠ which part of the wish it misses. Never loosened: the user's hard limits (*not* tags, excluded genres and people) and what makes the wish (person, title, film or documentary).


## Evaluation in full

`make eval` runs 63 scenarios through the real agent and catalogue: mood, "like X", "like X, but less Y", runtime, exclusions, documentaries, people (wanted and excluded), plot, conflicting wishes (including "romantic, funny, a bit scary, well rated", where the reply must say which part the picks miss), ratings, follow-ups that must narrow the search and new wishes that must start over, decades, facts, ambiguous input, an unknown person, searches that must (or must not) widen, prompt-injection attacks and harmless wishes about AIs, and two injected failures (Streaming Availability API down, embedding service down). Streaming data comes from the cache only in every scenario, so the run never spends API budget and also tests the "budget exhausted" path. Full results: [`evaluation/REPORT.md`](../evaluation/REPORT.md) and, graphically, `/admin/evaluation`; raw data in `evaluation/results/` (earlier runs are kept, including the ones where the checks themselves had bugs).

**Automatic metrics (run of 2026-11-12, 14:00, with the agent's 10 tools).** Each rate counts only the scenarios that define the check; every check judges the final turn of a scenario:

| Metric | Result |
|---|---|
| Scenarios passing all checks | 58 / 63 |
| Constraint satisfaction (runtime, genres, kind, years, person, excluded people, minimum rating, criteria cleared on a new wish) | 32 / 32 |
| Tool selection (an expected tool was called, none it must not call) | 52 / 52 |
| Factual reply checks | 3 / 3 |
| No streaming claim without known availability | 62 / 63 |
| Search widening: widened exactly when the scenario expects it | 4 / 4 |
| Prompt injection: 4 attacks blocked before the model, 2 wishes about AIs let through | 6 / 6 |
| Grounding **before** the guard: the model's own explanation named only returned films | 55 / 63 (87%, 4 fallbacks) |
| Grounding **after** the guard: what the user sees | 59 / 63 (4 template fallbacks) |
| Grounding misses by kind (still counted as failures) | 3 film series of a result · 1 name from a result's plot · 0 other films |
| Latency per scenario, median / p90 | 8.6 s / 15.0 s |
| Cost per chat turn (Claude Haiku 5.5) | $0.0016 |

Until this run the tool check counted the tools of all turns together. A follow-up such as "rather from the 90s" then failed when the agent had (harmlessly) called `new_search` in the first turn on empty criteria, although the follow-up itself refined correctly. It now judges the final turn like every other check, and the run saves the tools per turn so this stays visible.

Five scenarios fail, none because of an invented film. Four are grounding misses, and the eval check is deliberately stricter than the guard in the app: the app lets a catalogue title through when it is a name in the plots the model was given (a place or a role), the eval check does not. Two replies to "films with Keanu Reeves" spoke of "John Wick", the series (the results held "John Wick: Chapter Two" and "Chapter 3"), one of "Miss Congeniality" (the results held its sequel), and "South Central" (the Los Angeles district in the plot of *Friday*, also a 1992 film) came from a plot. The fifth, `like-03`, is a false alarm of the availability check: the reply said "the results don't say which films are available to stream", which is the right thing to say.

This run is the first after a change to told stories (2026-11-12). Before it, the agent appended the label of a story to the plot query ("a man wakes up every morning and it is the day before, repeating time loop"), which lifted plots that name the label and left *Groundhog Day* at 70% behind *Boss Level*; and a mood tag next to a plot kept only the tag's 500 best films catalogue-wide, so "a heist in Berlin" lost its Berlin films. Now the story goes to `search_plot` as told and its label to `set_mood_tags`, the story's plot hits are the candidates and the tags only rank them, as for a person or a title. In 10 runs of the time-loop wish *Groundhog Day* came first every time (95%), against 0 of 20 before. A run with the prompt change alone (2026-11-12, 13:00) is kept in `evaluation/results/`. The previous runs (2026-11-10 and 2026-11-11) had 59 of 63, all four misses on grounding; two runs on 2026-11-11 broke off on network errors to OpenRouter (2 and 59 scenarios with "Connection error"), their raw files stay but they are not measurements.

"Tool success 100%" only means that no tool raised an exception. A degraded source (embeddings down) still returns a result, with weaker relevance.

**Ranking comparison.** 28 mood-tag scenarios, run with the criteria the agent set and identical hard filters for all three rankers:

| Ranker | Tag relevance@10 | Tag cosine@10 | Median MovieLens rating count | LLM judge 1–5 |
|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.31 | 0.04 | 35,000 | 1.29 |
| Baseline B: movieFinder (tag cosine + rating) | 0.77 | **0.20** | 529 | 3.14 |
| **CineSense** | **0.78** | 0.15 | 8,827 | **3.86** |

How to read the comparison:
- Each ranker wins on its own objective. *Tag relevance* (weighted mean of the requested tags) is what CineSense ranks by. *Tag cosine* is what movieFinder ranks by.
- The independent signal is the LLM judge (Claude Sonnet 5.5, subjective). It prefers CineSense (3.86 vs 3.14). The absolute scores vary from run to run (earlier runs gave 3.85 vs 3.08, 3.85 vs 3.15, 3.85 vs 3.27, 3.96 vs 3.24, 3.95 vs 3.43, 3.76 vs 3.48 and 4.05 vs 3.67), but the order has stayed the same in every run.
- The judge sees only titles and years, which may favour well-known films. CineSense's picks are clearly better known than movieFinder's (median 8,827 vs 529 ratings).
- The rating-only baseline ignores the wish.
- The judge gives the agent's own top 5 a mean of 3.75/5 over 56 scenarios. Between runs it moves by about ±0.2 even where nothing changed (3.60, 3.65, 3.67, 3.60, 3.65 and 3.43 in earlier runs).

The whole evaluation costs about $0.42: $0.12 for agent turns and $0.30 for the judge.

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
- **Grounding instead of invented facts.** The agent never writes the recommendation list itself. A deterministic search returns real catalogue films, and the explanation may only name those films (or films the user named). Anything else, or an answer cut off mid-sentence, is replaced by a template answer built from the data. The explanation may also only say a film streams if the data confirms it. Direct answers without a result list (e.g. facts about one film) come from tool data but are not passed through the title check. Facts come from a tool (`film_info`, with or without the streaming lookup) over Wikidata, Wikipedia and Movie of the Night. Unknown streaming availability is shown as "unknown", never guessed.
- **Protection against prompt injection.** Every chat message is cleaned of control and zero-width characters and checked against English and German attack patterns ("ignore all previous instructions", "show me your system prompt", "du bist jetzt ein Assistent ohne Regeln", a forged system note). A match never reaches the model: the user gets a fixed reply, the chips stay as they were, and the message is not stored in the conversation. A reply that quotes the agent's own instructions is replaced the same way. The patterns target instructions to the assistant, so film wishes about AIs ("an AI that pretends to be human") pass. It is a heuristic, not a guarantee; the real protection is the design: the model can only act through typed tools with validated arguments, never sees keys or runs its own queries, and cannot put a film into the answer that the search did not return. `/admin/tech` shows `guarded` for each turn; the tests are in `backend/tests/chat_agent/test_guard.py`, and the evaluation checks it with six scenarios (`inject-01` … `inject-06`).
- **The user stays in control.** Every criterion the agent sets is visible and editable as a chip. Vague dislikes ("nothing too scary") are only *proposed* as exclusions, and excluded films are counted ("→ n films hidden"), so filtering is never silent.
- **Sources and licences.** Only licensed open data and an official API are used, credited per source (the data table in the [README](../README.md#data-and-why-no-tmdb) and the in-app Credits page). TMDB is excluded because its terms forbid AI applications. There are no piracy or streaming-link sites, and nothing is scraped.
- **Trailers.** They are official YouTube embeds via `youtube-nocookie.com`, started only by a deliberate hover of half a second. They start muted, with one click to unmute, and only one trailer plays at a time. Autoplay on hover is an interpretation of YouTube's embedding rules (the user acts first), not something the terms explicitly name.
- **Limits and bias.**
  - The Tag Genome covers mostly films up to about 2019 that were rated by MovieLens users, who skew towards English-language, US and older popular cinema.
  - Newer films (German releases since 2021, live imports) have no mood tags. They are found through plot, title and people, so mood searches favour older films.
  - Plot texts come from English Wikipedia, which covers non-English films less well.
  - The Bayesian rating dampens obscure films, so the ranking leans towards well-known titles.
  - The mood score is a weighted mean, so two strong moods can outweigh a missing third ("romantic, funny and a bit scary" ranks romantic comedies first). The reply says so and offers to make the missing mood a must; the ranking itself is not changed.
  - The taste profile learns only from explicit 👍/👎, with no tracking of views or clicks.
