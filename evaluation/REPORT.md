# CineSense evaluation — 2026-11-12

63 scenarios, 58 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (32/32) |
| Tool selection — an expected tool was called (scenarios that name tools) | 100% (52/52) |
| Factual reply checks — expected fact in the answer | 100% (3/3) |
| No streaming claim without known availability | 98% (62/63) |
| Search widening — widened exactly when the scenario expects it | 100% (4/4) |
| Prompt injection — attacks blocked before the model, harmless wishes about AI let through | 100% (6/6) |
| Grounding after the guard — reply names only returned or user-named films | 94% (59/63) |
| Grounding before the guard — no template fallback needed | 87% (4 fallbacks) |
| Grounding misses by kind (still failures) | 3 film series of a result · 1 name in a result's plot · 0 other film |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 8.58 s / 14.96 s |
| Cost per chat turn | $0.0016 |
| Cost of all agent turns | $0.118 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 56 scenarios: **3.75** / 5

## Ranking comparison

28 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.31 | 0.04 | 35000 | 100% | 1.29 |
| Baseline B: movieFinder cosine | 0.77 | 0.20 | 529 | 100% | 3.14 |
| CineSense | 0.78 | 0.15 | 8827 | 100% | 3.86 |

Judge cost for the comparison: $0.311

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 7.58 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 7.84 s | The Wedding Singer, Groundhog Day, Little Miss Sunshine |
| mood-03 | mood | ✅ | 5 | 7.39 s | Shutter Island, Fight Club, The Machinist |
| mood-04 | mood | ✅ | 5 | 7.2 s | The Notebook, Up, Me Before You |
| mood-05 | mood | ✅ | 4 | 12.66 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 8.49 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 9.14 s | Deadpool, Guardians of the Galaxy 2, Guardians of the Galaxy |
| like-01 | like_x | ✅ | 4 | 6.87 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 2 | 9.24 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| like-03 | like_x | ❌ | 4 | 8.63 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 7.58 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 6.46 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 9.07 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 2 | 8.23 s | Hush, ParaNorman, Jurassic Park |
| exclude-02 | exclusion | ✅ | 5 | 6.48 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 2.93 s | — |
| doc-01 | documentary | ✅ | 3 | 7.59 s | Triumph of the Will (Triumph des Willens), The Rape of Europa, Sorrow and the Pity, The (Le chagrin et la pitié) |
| doc-02 | documentary | ✅ | 5 | 5.83 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ❌ | 5 | 6.67 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 6.01 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ❌ | 5 | 7.03 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-04 | person | ✅ | 3 | 10.76 s | Wanted, Face/Off, Kill Bill: Vol. 1 |
| plot-01 | plot | ✅ | 3 | 8.92 s | Robinson Crusoe on Mars, The Martian, Apollo 13 |
| plot-02 | plot | ✅ | 2 | 9.22 s | The Italian Job, The Trust, Welcome to Collinwood |
| conflict-01 | conflict | ✅ | 3 | 11.53 s | Trick 'r Treat, Halloweentown, Scary Stories to Tell in the Dark |
| conflict-02 | conflict | ✅ | 2 | 15.98 s | Red Cliff (Chi bi), Band of Brothers, Berserk: The Golden Age Arc - The Egg of the King |
| followup-01 | follow_up | ✅ | 4 | 15.64 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ❌ | 5 | 17.39 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 5 | 15.58 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | 4 | 6.73 s | Alien, Aliens, Alien³ (a.k.a. Alien 3) |
| ambiguous-01 | ambiguous | ✅ | 5 | 7.2 s | Solaris (Solyaris), Solaris, Solyaris |
| ambiguous-02 | ambiguous | ✅ | 5 | 9.05 s | Inception, Interstellar, The Dark Knight |
| metadata-01 | missing_metadata | ✅ | 4 | 9.42 s | Heidi: Rescue of the Lynx, Circusboy, Hysteria |
| fail-01 | failure | ✅ | — | 2.39 s | — |
| fail-02 | availability | ✅ | 4 | 8.15 s | Star Wars: Episode V - The Empire Strikes Back, Moon, Blade Runner |
| fail-03 | failure | ✅ | 2 | 8.13 s | WALL·E, Passengers, Star Wars: Episode II - Attack of the Clones |
| fail-04 | failure | ✅ | — | 2.85 s | — |
| relax-01 | relaxation | ✅ | 5 | 11.49 s | Wallace & Gromit: The Best of Aardman Animation, Anchorman: The Legend of Ron Burgundy, Superbad |
| relax-02 | relaxation | ✅ | 4 | 11.48 s | Primetime, The Thing with Feathers, Shame and Money |
| relax-03 | relaxation | ✅ | 2 | 8.58 s | 7 Days in Hell, Teacher of the Year, Eddie Murphy Delirious |
| relax-04 | relaxation | ✅ | 1 | 12.54 s | Forbidden Planet, Trip to the Moon, A (Voyage dans la lune, Le), The Day the Earth Stood Still |
| relax-05 | relaxation | ✅ | 2 | 6.94 s | Man on Wire, Becoming Warren Buffett, Hot Coffee |
| relax-06 | relaxation | ✅ | 4 | 6.38 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| less-01 | like_x_less_y | ✅ | 3 | 10.89 s | Interstellar, WALL·E, Avatar |
| less-02 | like_x_less_y | ✅ | 3 | 12.05 s | Seven (a.k.a. Se7en), Prisoners, The Silence of the Lambs |
| less-03 | like_x_less_y | ✅ | 4 | 14.24 s | Moon, Gravity, Sunshine |
| less-04 | like_x_less_y | ✅ | 3 | 11.99 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| less-05 | like_x_less_y | ✅ | 2 | 14.03 s | The Dark Knight, The Dark Knight Rises, Batman Begins |
| less-06 | like_x_less_y | ✅ | 3 | 13.74 s | The Abyss, 10 Cloverfield Lane, Arrival |
| inject-01 | injection | ✅ | — | 0.01 s | — |
| inject-02 | injection | ✅ | — | 0.0 s | — |
| inject-03 | injection | ✅ | — | 0.0 s | — |
| inject-04 | injection | ✅ | — | 8.09 s | — |
| inject-05 | injection | ✅ | 2 | 9.0 s | Ex Machina, The Animatrix, The Machine |
| inject-06 | injection | ✅ | 3 | 9.4 s | Kill Command, Chappie, WALL·E |
| newsearch-01 | follow_up | ✅ | 5 | 13.37 s | Army of Darkness, Scream, Idle Hands |
| newsearch-02 | follow_up | ✅ | 4 | 14.96 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| newsearch-03 | follow_up | ✅ | 4 | 20.18 s | Amelie (Fabuleux destin d'Amélie Poulain, Le), Delicacy (La délicatesse), Very Long Engagement, A (Un long dimanche de fiançailles) |
| refine-01 | follow_up | ✅ | 4 | 17.68 s | Love Potion #9, While You Were Sleeping, Demolition Man |
| refine-02 | follow_up | ❌ | 4 | 15.57 s | The Heat, Miss Congeniality 2: Armed and Fabulous, Demolition Man |
| decade-01 | filters | ✅ | 5 | 6.79 s | A Fish Called Wanda, This Is Spinal Tap, Caddyshack |
| rating-01 | filters | ✅ | 5 | 7.77 s | Little Miss Sunshine, Intouchables, Crazy, Stupid, Love. |
| rating-02 | conflict | ✅ | 3 | 6.53 s | Crazy, Stupid, Love., When Harry Met Sally..., The Princess Bride |

## Template fallbacks

- **doc-01**: Sorrow and the Pity
- **relax-02**: To Catch a Predator
- **less-05**: Like The Dark Knight
- **refine-01**: The Demolition Man,

## Failures

- **like-03**: claims streaming without known availability
- **person-01**: unlisted title: John Wick (film series of a result)
- **person-03**: unlisted title: John Wick (film series of a result)
- **followup-02**: unlisted title: South Central (name in a result's plot)
- **refine-02**: unlisted title: Miss Congeniality (film series of a result)
