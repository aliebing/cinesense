# CineSense evaluation — 2026-11-02

48 scenarios, 47 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (24/24) |
| Tool selection — an expected tool was called (scenarios that name tools) | 98% (40/41) |
| Factual reply checks — expected fact in the answer | 100% (2/2) |
| No streaming claim without known availability | 100% (48/48) |
| Search widening — widened exactly when the scenario expects it | 100% (4/4) |
| Grounding after the guard — reply names only returned or user-named films | 100% (48/48) |
| Grounding before the guard — no template fallback needed | 90% (5 fallbacks) |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 7.65 s / 12.74 s |
| Cost per chat turn | $0.0014 |
| Cost of all agent turns | $0.069 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 43 scenarios: **3.58** / 5

## Ranking comparison

21 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.34 | 0.05 | 35000 | 100% | 1.29 |
| Baseline B: movieFinder cosine | 0.78 | 0.20 | 657 | 100% | 3.48 |
| CineSense | 0.84 | 0.16 | 10863 | 100% | 3.76 |

Judge cost for the comparison: $0.202

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 7.53 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 8.05 s | The Wedding Singer, Little Miss Sunshine, Groundhog Day |
| mood-03 | mood | ✅ | 5 | 7.58 s | Shutter Island, Fight Club, The Machinist |
| mood-04 | mood | ✅ | 5 | 6.69 s | The Notebook, Up, Me Before You |
| mood-05 | mood | ✅ | 4 | 11.28 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 9.07 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 7.24 s | Deadpool, Guardians of the Galaxy 2, Guardians of the Galaxy |
| like-01 | like_x | ✅ | 4 | 7.6 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 2 | 8.87 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| like-03 | like_x | ✅ | 4 | 7.62 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 8.01 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 6.58 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 7.41 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 2 | 7.0 s | Hush, ParaNorman, Jurassic Park |
| exclude-02 | exclusion | ✅ | 5 | 8.02 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 2.83 s | — |
| doc-01 | documentary | ✅ | 3 | 7.68 s | Triumph of the Will (Triumph des Willens), The Rape of Europa, Sorrow and the Pity, The (Le chagrin et la pitié) |
| doc-02 | documentary | ✅ | 5 | 5.26 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ✅ | 5 | 7.39 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 6.01 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ✅ | 5 | 6.57 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| plot-01 | plot | ✅ | 3 | 7.92 s | The Martian, Pandorum, Interstellar |
| plot-02 | plot | ✅ | 2 | 6.7 s | M, Edukators, The (Die Fetten Jahre sind vorbei), Wings of Desire (Himmel über Berlin, Der) |
| conflict-01 | conflict | ✅ | 2 | 8.56 s | The Sixth Sense, Get Out, The Others |
| conflict-02 | conflict | ✅ | 2 | 12.23 s | Red Cliff (Chi bi), Band of Brothers, Red Cliff Part II (Chi Bi Xia: Jue Zhan Tian Xia) |
| followup-01 | follow_up | ✅ | 4 | 13.3 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ✅ | 5 | 15.53 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 5 | 15.29 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | — | 2.52 s | — |
| ambiguous-01 | ambiguous | ❌ | 4 | 5.43 s | Solaris (Solyaris), Solaris, Solyaris |
| ambiguous-02 | ambiguous | ✅ | — | 1.91 s | — |
| metadata-01 | missing_metadata | ✅ | 4 | 10.96 s | Eldorado: Everything the Nazis Hate, Heidi: Rescue of the Lynx, Silent Friend |
| fail-01 | failure | ✅ | — | 2.28 s | — |
| fail-02 | availability | ✅ | 4 | 6.66 s | Star Wars: Episode V - The Empire Strikes Back, Blade Runner, Children of Men |
| fail-03 | failure | ✅ | 2 | 12.74 s | The Adjustment Bureau, Passengers, Her |
| fail-04 | failure | ✅ | — | 3.1 s | — |
| relax-01 | relaxation | ✅ | 2 | 10.25 s | Digger, Whalefall, Other Mommy |
| relax-02 | relaxation | ✅ | 4 | 12.82 s | The Dark Knight, Seven (a.k.a. Se7en), Batman Begins |
| relax-03 | relaxation | ✅ | 2 | 7.29 s | Nikitich and The Dragon, 7 Days in Hell, Teacher of the Year |
| relax-04 | relaxation | ✅ | 1 | 12.02 s | Forbidden Planet, Trip to the Moon, A (Voyage dans la lune, Le), The Day the Earth Stood Still |
| relax-05 | relaxation | ✅ | 2 | 6.37 s | Man on Wire, Becoming Warren Buffett, Hot Coffee |
| relax-06 | relaxation | ✅ | 4 | 6.49 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| less-01 | like_x_less_y | ✅ | 3 | 12.03 s | Interstellar, WALL·E, The Matrix |
| less-02 | like_x_less_y | ✅ | 3 | 14.65 s | Seven (a.k.a. Se7en), Prisoners, The Silence of the Lambs |
| less-03 | like_x_less_y | ✅ | 4 | 11.51 s | Moon, Passengers, Gravity |
| less-04 | like_x_less_y | ✅ | 3 | 12.41 s | Before Sunset, Amelie (Fabuleux destin d'Amélie Poulain, Le), Before Midnight |
| less-05 | like_x_less_y | ✅ | 2 | 11.6 s | The Dark Knight, The Dark Knight Rises, Batman Begins |
| less-06 | like_x_less_y | ✅ | 3 | 8.94 s | The Abyss, 10 Cloverfield Lane, Close Encounters of the Third Kind |

## Template fallbacks

- **runtime-02**: South Central
- **doc-01**: Triumph of the Will, Sorrow and the Pity, The
- **person-01**: John Wick
- **person-03**: John Wick
- **followup-02**: South Central

## Failures

- **ambiguous-01**: expected one of ['similar_to', 'film_facts', 'set_mood_tags'], called ['find_title']
