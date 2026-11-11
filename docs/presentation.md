# CineSense — presentation outline (10 min + 5 min Q&A)

Framing: **SCR** (Situation → Complication → Resolution). Each section is about 1.5 minutes. A live demo runs inside section 2.

## 1. The problem (Situation → Complication)

- **Situation:** tonight's film is chosen by scrolling. Cinema sites, Netflix and Prime each show their own long lists and genre grids.
- **Complication:** real wishes combine several things, for example "something like Interstellar but shorter, no horror, on a service I have". No site lets you say that. Sites that try with AI often invent titles. And it feels like a database, not like going to the movies.
- **Who it is for:** anyone in Germany deciding between the cinema and their streaming services. Built for one real user, Alexander.

## 2. The solution (Resolution) — demo

- **Cinematic UI:** a 2.29:1 screen, curtains, fog and light. Seven mood worlds change in the background; for each, the homepage shows its newest top-rated films (last 8 years) and its top classics, and the drifting titles are those films. Trailers play on hover.
- **Chat agent (LangGraph ReAct, Claude Haiku 5.5 via OpenRouter, 10 tools):** it turns the wish into **visible chips**: mood tags with weight and prefer/must/not, filters, person, plot.
- **Search page:** the best matches in front (up to 6, at least 3), the further ones below from 70, 60 or 50% by how many strong films there are; too few films for every wish show the smallest widening below, while the search itself stays.
- **The search is deterministic and explainable:** "dark 80% · space travel 99% · streaming on Netflix", and "→ 214 films hidden" for exclusions.
- **Grounding:** the reply may only name films the search returned. Otherwise a template answer is used.
- **Personalisation:** 👍/👎 build an anonymous taste profile ("virtual reality · cyberpunk · dark hero"). ⚡/😂 steer only the current session.
- **Demo script:**
  1. Homepage: "funny or action, Marvel welcome, no horror". The chips appear, then the picks with trailers.
  2. "shorter please". `max_runtime` is set.
  3. Click a pick to open the stage. Show streaming in Germany, the trailer, 👍, and the row re-ranking.
  4. Open the genre drawer. The same conversation continues.
  5. 👤 profile panel and reset.

## 3. The data

- **No TMDB:** its terms forbid AI apps. Open data instead:
  - MovieLens Tag Genome: 1,128 mood tags per film, about 19,800 films
  - Wikidata: people, runtime, German release, trailer ids
  - English Wikipedia plots: chunked, embedded with `text-embedding-3-small`, about 1,536-dim vectors in pgvector
  - plus about 800 German releases since 2021
- **Streaming Availability API:** streaming in Germany, posters. The free plan has 1,000 requests/month, guarded by a cache, a budget of 900 and a circuit breaker.
- **Extended live search** for newer films and people, imported lazily.
- **Ingest:** resumable, rate-limit tolerant. Embedding cost was about $0.30 for the whole catalogue.

## 4. Evaluation

- **63 scenarios**, run through the real agent and catalogue: moods, "like X, but less Y", people wanted and excluded, conflicts, follow-ups, prompt-injection attacks and injected API failures.
- **Automatic results** (`evaluation/REPORT.md`, run of 2026-11-10 with the 10 tools):
  - 59/63 pass every check
  - constraints 32/32, tool selection 51/52, prompt injection 6/6
  - grounding: users saw 60/63 grounded replies; three named a film series or a plot title ("John Wick" for "John Wick: Chapter Two")
  - median latency 8.7 s, **$0.0016 per chat turn**
- **Ranking comparison** on 26 mood scenarios, with identical criteria and filters:

  | | Tag relevance@10 | Tag cosine@10 | LLM judge (Sonnet 5.5) |
  |---|---|---|---|
  | Filters + Bayesian rating | 0.35 | 0.05 | 1.54 |
  | movieFinder cosine | 0.78 | 0.20 | 3.15 |
  | **CineSense** | **0.79** | 0.15 | **3.85** |

  Each ranker wins on its own metric. The judge prefers CineSense, which also picks better-known films. Caveat: the judge sees titles only.
- **Honesty:** the first runs exposed bugs in the checks, and an independent review found that a "fix" had weakened the title guard; both were repaired and re-run. A full run costs about $0.42.

## 5. Challenges

- **Cosine over 1,128 tags flattered obscure films** ("Critters 4" for "dark space"). Live testing showed this. The weighted mean of only the requested tags fixed it.
- **Parallel tool calls raced on the shared criteria.** Tools now run sequentially, each on the previous result.
- **Reasoning tokens truncated the explanation.** The token budget was raised and truncated answers fall back to the template.
- **The ReAct round limit left unanswered tool calls**, which broke the next turn. The limit now always presents and closes the open calls. An independent code review found this.
- **Look and feel:** many iterations on the curtain, screen ratio and fog until it felt like a cinema.

## 6. What's next

- Mood tags for new films, e.g. predicting Tag Genome relevance from plot embeddings.
- Personalising the home rows. History trimming and per-thread token budgets.
- Feedback inside the chat ("not this one").
- **Log-in and user management** (with consent): a lasting taste profile per user instead of a browser id.
- **Several search sessions per user, like the chats in ChatGPT:** a list of past searches to go back to, kept in a Postgres checkpointer instead of process memory.
- More languages: German Wikipedia plots, a German UI.
