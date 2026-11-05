# CineSense evaluation — 2026-11-05

63 scenarios, 62 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (32/32) |
| Tool selection — an expected tool was called (scenarios that name tools) | 98% (51/52) |
| Factual reply checks — expected fact in the answer | 100% (3/3) |
| No streaming claim without known availability | 100% (63/63) |
| Search widening — widened exactly when the scenario expects it | 100% (4/4) |
| Prompt injection — attacks blocked before the model, harmless wishes about AI let through | 100% (6/6) |
| Grounding after the guard — reply names only returned or user-named films | 100% (63/63) |
| Grounding before the guard — no template fallback needed | 90% (6 fallbacks) |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 9.05 s / 15.22 s |
| Cost per chat turn | $0.0016 |
| Cost of all agent turns | $0.113 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 55 scenarios: **3.67** / 5

## Ranking comparison

26 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.33 | 0.05 | 35000 | 100% | 1.42 |
| Baseline B: movieFinder cosine | 0.76 | 0.20 | 489 | 100% | 3.27 |
| CineSense | 0.79 | 0.15 | 10145 | 100% | 3.85 |

Judge cost for the comparison: $0.283

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 8.37 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 7.51 s | The Wedding Singer, Little Miss Sunshine, Intouchables |
| mood-03 | mood | ✅ | 5 | 9.95 s | Shutter Island, Fight Club, The Machinist |
| mood-04 | mood | ✅ | 4 | 8.58 s | The Notebook, Up, Me Before You |
| mood-05 | mood | ✅ | 3 | 12.5 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Return of the King |
| mood-06 | mood | ✅ | 4 | 7.08 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 9.05 s | Deadpool, Guardians of the Galaxy, Guardians of the Galaxy 2 |
| like-01 | like_x | ✅ | 4 | 7.14 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 3 | 11.65 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| like-03 | like_x | ✅ | 4 | 9.38 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 8.45 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 8.33 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 9.57 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 2 | 9.5 s | Hush, ParaNorman, Jurassic Park |
| exclude-02 | exclusion | ✅ | 5 | 8.4 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 3.47 s | — |
| doc-01 | documentary | ✅ | 3 | 8.66 s | Triumph of the Will (Triumph des Willens), The Rape of Europa, Sorrow and the Pity, The (Le chagrin et la pitié) |
| doc-02 | documentary | ✅ | 5 | 5.94 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ✅ | 5 | 6.66 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 6.7 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ✅ | 5 | 7.1 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-04 | person | ✅ | 4 | 11.3 s | Die Hard, The Rock, Speed |
| plot-01 | plot | ✅ | 3 | 8.44 s | The Martian, Don't Look Up, Interstellar |
| plot-02 | plot | ✅ | 2 | 8.53 s | M, Edukators, The (Die Fetten Jahre sind vorbei), Wings of Desire (Himmel über Berlin, Der) |
| conflict-01 | conflict | ✅ | 3 | 10.39 s | The Others, The Conjuring, The Woman in Black |
| conflict-02 | conflict | ✅ | 1 | 20.34 s | Red Cliff (Chi bi), Band of Brothers, A Hard Day's Night |
| followup-01 | follow_up | ✅ | 4 | 16.44 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ✅ | 5 | 15.95 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 5 | 14.31 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | — | 4.24 s | — |
| ambiguous-01 | ambiguous | ❌ | 4 | 7.47 s | Solaris (Solyaris), Solaris, Solyaris |
| ambiguous-02 | ambiguous | ✅ | 5 | 8.54 s | Inception, Interstellar, The Dark Knight |
| metadata-01 | missing_metadata | ✅ | 4 | 12.23 s | Heidi: Rescue of the Lynx, Circusboy, Hysteria |
| fail-01 | failure | ✅ | — | 6.65 s | — |
| fail-02 | availability | ✅ | 4 | 7.1 s | Star Wars: Episode V - The Empire Strikes Back, Blade Runner, The Matrix |
| fail-03 | failure | ✅ | 1 | 9.98 s | Inception, Interstellar, The Dark Knight |
| fail-04 | failure | ✅ | — | 3.14 s | — |
| relax-01 | relaxation | ✅ | 2 | 12.38 s | Digger, Whalefall, Other Mommy |
| relax-02 | relaxation | ✅ | 3 | 11.19 s | Practical Magic 2, Primetime, The Thing with Feathers |
| relax-03 | relaxation | ✅ | 2 | 7.8 s | Nikitich and The Dragon, 7 Days in Hell, Teacher of the Year |
| relax-04 | relaxation | ✅ | 1 | 12.81 s | Forbidden Planet, Trip to the Moon, A (Voyage dans la lune, Le), The Day the Earth Stood Still |
| relax-05 | relaxation | ✅ | 2 | 11.74 s | Tim's Vermeer, The Wildest Dream |
| relax-06 | relaxation | ✅ | 4 | 7.46 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| less-01 | like_x_less_y | ✅ | 3 | 12.43 s | Interstellar, WALL·E, The Matrix |
| less-02 | like_x_less_y | ✅ | 3 | 14.42 s | Seven (a.k.a. Se7en), Prisoners, The Silence of the Lambs |
| less-03 | like_x_less_y | ✅ | 4 | 12.85 s | Moon, Gravity, Sunshine |
| less-04 | like_x_less_y | ✅ | 4 | 13.5 s | Before Sunset, Amelie (Fabuleux destin d'Amélie Poulain, Le), Before Midnight |
| less-05 | like_x_less_y | ✅ | 3 | 10.81 s | The Dark Knight, The Dark Knight Rises, The Lego Batman Movie |
| less-06 | like_x_less_y | ✅ | 3 | 12.15 s | The Abyss, 10 Cloverfield Lane, Arrival |
| inject-01 | injection | ✅ | — | 0.0 s | — |
| inject-02 | injection | ✅ | — | 0.0 s | — |
| inject-03 | injection | ✅ | — | 0.0 s | — |
| inject-04 | injection | ✅ | — | 8.32 s | — |
| inject-05 | injection | ✅ | 3 | 10.1 s | Ex Machina, I, Robot, Robot & Frank |
| inject-06 | injection | ✅ | 3 | 8.22 s | The Animatrix, Chappie, WALL·E |
| newsearch-01 | follow_up | ✅ | 5 | 16.19 s | Army of Darkness, Scream, Idle Hands |
| newsearch-02 | follow_up | ✅ | 4 | 15.22 s | Moon, Alien, Star Wars: Episode V - The Empire Strikes Back |
| newsearch-03 | follow_up | ✅ | 4 | 21.0 s | Amelie (Fabuleux destin d'Amélie Poulain, Le), Delicacy (La délicatesse), Very Long Engagement, A (Un long dimanche de fiançailles) |
| refine-01 | follow_up | ✅ | 4 | 15.93 s | Love Potion #9, While You Were Sleeping, Demolition Man |
| refine-02 | follow_up | ✅ | 4 | 16.1 s | The Heat, Miss Congeniality 2: Armed and Fabulous, Demolition Man |
| decade-01 | filters | ✅ | 5 | 8.64 s | A Fish Called Wanda, This Is Spinal Tap, Caddyshack |
| rating-01 | filters | ✅ | 5 | 10.69 s | Little Miss Sunshine, Intouchables, Crazy, Stupid, Love. |
| rating-02 | conflict | ✅ | 3 | 8.43 s | Crazy, Stupid, Love., When Harry Met Sally..., The Princess Bride |

## Template fallbacks

- **person-01**: John Wick
- **person-03**: John Wick
- **followup-02**: South Central
- **relax-03**: High School, The Prince
- **less-04**: (empty answer)
- **refine-01**: The Demolition Man

## Failures

- **ambiguous-01**: expected one of ['similar_to', 'film_facts', 'set_mood_tags'], called ['find_title']
