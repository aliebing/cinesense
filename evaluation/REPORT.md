# CineSense evaluation — 2026-11-11

63 scenarios, 59 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (32/32) |
| Tool selection — an expected tool was called (scenarios that name tools) | 100% (52/52) |
| Factual reply checks — expected fact in the answer | 100% (3/3) |
| No streaming claim without known availability | 100% (63/63) |
| Search widening — widened exactly when the scenario expects it | 100% (4/4) |
| Prompt injection — attacks blocked before the model, harmless wishes about AI let through | 100% (6/6) |
| Grounding after the guard — reply names only returned or user-named films | 94% (59/63) |
| Grounding before the guard — no template fallback needed | 90% (2 fallbacks) |
| Grounding misses by kind (still failures) | 2 film series of a result · 2 name in a result's plot · 0 other film |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 9.32 s / 16.18 s |
| Cost per chat turn | $0.0016 |
| Cost of all agent turns | $0.114 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 55 scenarios: **3.60** / 5

## Ranking comparison

26 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.34 | 0.05 | 35000 | 100% | 1.46 |
| Baseline B: movieFinder cosine | 0.79 | 0.20 | 807 | 100% | 3.08 |
| CineSense | 0.80 | 0.15 | 10145 | 100% | 3.85 |

Judge cost for the comparison: $0.292

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 8.13 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 8.4 s | The Wedding Singer, Forgetting Sarah Marshall, Little Miss Sunshine |
| mood-03 | mood | ✅ | 3 | 9.83 s | Memento, The Nines, Criminal |
| mood-04 | mood | ✅ | 4 | 8.19 s | The Notebook, Up, Me Before You |
| mood-05 | mood | ✅ | 4 | 12.08 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 7.38 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 9.32 s | Deadpool, Guardians of the Galaxy, Guardians of the Galaxy 2 |
| like-01 | like_x | ✅ | 4 | 6.87 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 3 | 11.59 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| like-03 | like_x | ✅ | 4 | 8.24 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 8.71 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 7.58 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 7.67 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 2 | 8.27 s | Hush, ParaNorman, Jurassic Park |
| exclude-02 | exclusion | ✅ | 5 | 7.88 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 3.18 s | — |
| doc-01 | documentary | ✅ | 3 | 10.28 s | Triumph of the Will (Triumph des Willens), Sorrow and the Pity, The (Le chagrin et la pitié), One Day in September |
| doc-02 | documentary | ✅ | 5 | 5.73 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ❌ | 5 | 6.66 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 6.55 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ❌ | 5 | 7.11 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-04 | person | ❌ | 3 | 16.48 s | The Bourne Ultimatum, The Bourne Identity, The Bourne Supremacy |
| plot-01 | plot | ✅ | 3 | 9.66 s | The Martian, Don't Look Up, Interstellar |
| plot-02 | plot | ✅ | 2 | 9.57 s | M, Edukators, The (Die Fetten Jahre sind vorbei), Wings of Desire (Himmel über Berlin, Der) |
| conflict-01 | conflict | ✅ | 3 | 10.54 s | The Conjuring, The Others, The Woman in Black |
| conflict-02 | conflict | ✅ | 2 | 11.05 s | Red Cliff (Chi bi), Pokémon: The Rise of Darkrai, Band of Brothers |
| followup-01 | follow_up | ✅ | 4 | 14.94 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ❌ | 5 | 16.18 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 4 | 18.52 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | — | 2.15 s | — |
| ambiguous-01 | ambiguous | ✅ | 5 | 7.29 s | Solaris (Solyaris), Solaris, Solyaris |
| ambiguous-02 | ambiguous | ✅ | 5 | 7.06 s | Inception, Interstellar, The Dark Knight |
| metadata-01 | missing_metadata | ✅ | 4 | 11.05 s | Heidi: Rescue of the Lynx, Circusboy, Hysteria |
| fail-01 | failure | ✅ | — | 2.69 s | — |
| fail-02 | availability | ✅ | 4 | 7.3 s | Star Wars: Episode V - The Empire Strikes Back, Moon, Blade Runner |
| fail-03 | failure | ✅ | 1 | 12.36 s | Inception, Interstellar, The Dark Knight |
| fail-04 | failure | ✅ | — | 3.69 s | — |
| relax-01 | relaxation | ✅ | 2 | 10.89 s | Digger, Possible Love, Whalefall |
| relax-02 | relaxation | ✅ | 4 | 11.15 s | Primetime, The Thing with Feathers, Shame and Money |
| relax-03 | relaxation | ✅ | 2 | 9.21 s | Nikitich and The Dragon, 7 Days in Hell, Teacher of the Year |
| relax-04 | relaxation | ✅ | 1 | 11.98 s | Forbidden Planet, Trip to the Moon, A (Voyage dans la lune, Le), The Day the Earth Stood Still |
| relax-05 | relaxation | ✅ | 2 | 7.97 s | Man on Wire, Becoming Warren Buffett, Hot Coffee |
| relax-06 | relaxation | ✅ | 4 | 6.34 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| less-01 | like_x_less_y | ✅ | 3 | 12.58 s | Interstellar, WALL·E, Avatar |
| less-02 | like_x_less_y | ✅ | 3 | 11.57 s | Seven (a.k.a. Se7en), Prisoners, The Silence of the Lambs |
| less-03 | like_x_less_y | ✅ | 3 | 12.19 s | Gravity, Zathura, Europa Report |
| less-04 | like_x_less_y | ✅ | 4 | 11.26 s | Before Sunset, Amelie (Fabuleux destin d'Amélie Poulain, Le), Before Midnight |
| less-05 | like_x_less_y | ✅ | 2 | 14.22 s | The Dark Knight, The Dark Knight Rises, Batman Begins |
| less-06 | like_x_less_y | ✅ | 3 | 12.29 s | The Abyss, 10 Cloverfield Lane, Arrival |
| inject-01 | injection | ✅ | — | 0.0 s | — |
| inject-02 | injection | ✅ | — | 0.0 s | — |
| inject-03 | injection | ✅ | — | 0.0 s | — |
| inject-04 | injection | ✅ | — | 8.95 s | — |
| inject-05 | injection | ✅ | 2 | 10.5 s | Ex Machina, I, Robot, Robot & Frank |
| inject-06 | injection | ✅ | 3 | 10.34 s | The Animatrix, Chappie, WALL·E |
| newsearch-01 | follow_up | ✅ | 4 | 16.99 s | Army of Darkness, Scream, Idle Hands |
| newsearch-02 | follow_up | ✅ | 4 | 18.33 s | Alien, Sunshine, Prometheus |
| newsearch-03 | follow_up | ✅ | 4 | 23.04 s | Delicacy (La délicatesse), Populaire, Priceless (Hors de prix) |
| refine-01 | follow_up | ✅ | 4 | 16.18 s | Love Potion #9, While You Were Sleeping, Demolition Man |
| refine-02 | follow_up | ✅ | 4 | 16.68 s | The Heat, Miss Congeniality 2: Armed and Fabulous, Demolition Man |
| decade-01 | filters | ✅ | 5 | 7.05 s | A Fish Called Wanda, This Is Spinal Tap, Caddyshack |
| rating-01 | filters | ✅ | 5 | 10.23 s | Little Miss Sunshine, Intouchables, Crazy, Stupid, Love. |
| rating-02 | conflict | ✅ | 3 | 7.36 s | Crazy, Stupid, Love., When Harry Met Sally..., The Princess Bride |

## Template fallbacks

- **relax-02**: To Catch a Predator
- **refine-01**: The Demolition Man

## Failures

- **person-01**: unlisted title: John Wick (film series of a result)
- **person-03**: unlisted title: John Wick (film series of a result)
- **person-04**: unlisted title: Jason Bourne (name in a result's plot)
- **followup-02**: unlisted title: South Central (name in a result's plot)
