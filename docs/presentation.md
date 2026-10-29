# CineSense — presentation outline (10 min + 5 min Q&A)

Framing: **SCR** (Situation → Complication → Resolution). Each section is about 1.5 minutes. A live demo runs inside section 2.

## 1. The problem (Situation → Complication)

- **Situation:** tonight's film is chosen by scrolling. Cinema sites, Netflix and Prime each show their own long lists and genre grids.
- **Complication:** real wishes combine several things, for example "something like Interstellar but shorter, no horror, on a service I have". No site lets you say that. Sites that try with AI often invent titles. And it feels like a database, not like going to the movies.
- **Who it is for:** anyone in Germany deciding between the cinema and their streaming services. Built for one real user, Alexander.

## 2. The solution (Resolution) — demo

- **Cinematic UI:** a 2.29:1 screen, curtains, fog and light. Mood worlds change in the background, and the tile rows follow the active world. Trailers play on hover.
- **Chat agent (LangGraph ReAct, Claude Haiku 5.5 via OpenRouter):** it turns the wish into **visible chips**: mood tags with weight and prefer/must/not, filters, person, plot.
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

- **36 scenarios**, run through the real agent and catalogue:
  - mood, "like X", runtime, exclusions, documentaries, people, plot, conflicts, follow-ups, facts, ambiguous wishes
  - 4 injected failures: streaming down, budget exhausted, embeddings down, unknown person
- **Automatic results** (see `eval/REPORT.md`):
  - constraint satisfaction 97%
  - tool selection 100%, tool success 100%
  - grounding 97%
  - median latency 7.4 s
  - **$0.001 per chat turn**
- **Ranking comparison** on identical criteria and filters:

  | | Tag relevance@10 | LLM judge (Sonnet 5.5) |
  |---|---|---|
  | Filters + Bayesian rating | 0.32 | 1.36 |
  | movieFinder cosine | 0.78 | 3.41 |
  | **CineSense** | **0.85** | **3.82** |

  CineSense also picks better-known films than cosine (median 3,977 vs 926 MovieLens ratings).
- **Total cost** of the evaluation, including the judge: about $0.25.

## 5. Challenges

- **Cosine over 1,128 tags flattered obscure films** ("Critters 4" for "dark space"). Live testing showed this. The weighted mean of only the requested tags fixed it.
- **Parallel tool calls raced on the shared criteria.** Tools now run sequentially, each on the previous result.
- **Reasoning tokens truncated the explanation.** The token budget was raised and truncated answers fall back to the template.
- **The ReAct round limit left unanswered tool calls**, which broke the next turn. The limit now always presents and closes the open calls. An independent code review found this.
- **Look and feel:** many iterations on the curtain, screen ratio and fog until it felt like a cinema.

## 6. What's next

- Mood tags for new films, e.g. predicting Tag Genome relevance from plot embeddings.
- Personalising the home rows. History trimming and per-thread token budgets.
- Feedback inside the chat ("not this one"). A multi-user deployment with real accounts and consent.
- More languages: German Wikipedia plots, a German UI.
