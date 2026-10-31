# CineSense evaluation — 2026-10-31

36 scenarios, 36 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (19/19) |
| Tool selection — an expected tool was called (scenarios that name tools) | 100% (35/35) |
| Factual reply checks — expected fact in the answer | 100% (2/2) |
| No streaming claim without known availability | 100% (36/36) |
| Grounding after the guard — reply names only returned or user-named films | 100% (36/36) |
| Grounding before the guard — no template fallback needed | 86% (5 fallbacks) |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 7.53 s / 12.3 s |
| Cost per chat turn | $0.0011 |
| Cost of all agent turns | $0.044 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 31 scenarios: **3.97** / 5

## Ranking comparison

21 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.34 | 0.05 | 35000 | 100% | 1.52 |
| Baseline B: movieFinder cosine | 0.79 | 0.20 | 1118 | 100% | 3.67 |
| CineSense | 0.84 | 0.16 | 10354 | 100% | 4.05 |

Judge cost for the comparison: $0.176

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 6.77 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 6.98 s | Intouchables, Little Miss Sunshine, Hunt for the Wilderpeople |
| mood-03 | mood | ✅ | 3 | 11.52 s | Shutter Island, Criminal, The Illusionist |
| mood-04 | mood | ✅ | 4 | 8.14 s | The Notebook, Up, Me Before You |
| mood-05 | mood | ✅ | 4 | 10.07 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 8.24 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 7.01 s | Deadpool, Guardians of the Galaxy 2, Guardians of the Galaxy |
| like-01 | like_x | ✅ | 4 | 8.44 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 4 | 11.41 s | Amelie (Fabuleux destin d'Amélie Poulain, Le), Chocolat, Midnight in Paris |
| like-03 | like_x | ✅ | 4 | 7.72 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 8.43 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 6.8 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 5.58 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 5 | 8.45 s | Jurassic Park, One Hour Photo, Nightcrawler |
| exclude-02 | exclusion | ✅ | 5 | 6.19 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 2.55 s | — |
| doc-01 | documentary | ✅ | 4 | 7.28 s | Triumph of the Will (Triumph des Willens), The Rape of Europa, Sorrow and the Pity, The (Le chagrin et la pitié) |
| doc-02 | documentary | ✅ | 5 | 5.76 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ✅ | 5 | 6.09 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 5.52 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ✅ | 5 | 7.37 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| plot-01 | plot | ✅ | 3 | 8.35 s | The Martian, Pandorum, Interstellar |
| plot-02 | plot | ✅ | 2 | 9.15 s | M, Edukators, The (Die Fetten Jahre sind vorbei), Wings of Desire (Himmel über Berlin, Der) |
| conflict-01 | conflict | ✅ | 3 | 10.59 s | The Conjuring, The Others, Insidious |
| conflict-02 | conflict | ✅ | 2 | 12.74 s | Red Cliff (Chi bi), Pokémon: The Rise of Darkrai, Band of Brothers |
| followup-01 | follow_up | ✅ | 4 | 14.17 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ✅ | 5 | 12.74 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 5 | 13.35 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | — | 3.25 s | — |
| ambiguous-01 | ambiguous | ✅ | 3 | 7.68 s | Interstellar, Moon, The Martian |
| ambiguous-02 | ambiguous | ✅ | — | 2.34 s | — |
| metadata-01 | missing_metadata | ✅ | 3 | 4.82 s | Gentle Monster |
| fail-01 | failure | ✅ | — | 2.11 s | — |
| fail-02 | availability | ✅ | 4 | 6.06 s | Star Wars: Episode V - The Empire Strikes Back, Blade Runner, Children of Men |
| fail-03 | failure | ✅ | 2 | 12.3 s | The Adjustment Bureau, Passengers, Her |
| fail-04 | failure | ✅ | — | 3.25 s | — |

## Template fallbacks

- **mood-02**: Waking Ned Devine
- **mood-05**: King Richard
- **person-01**: John Wick
- **person-03**: John Wick
- **followup-02**: South Central

## Failures

None.
