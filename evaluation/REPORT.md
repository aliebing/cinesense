# CineSense evaluation — 2026-11-05

61 scenarios, 60 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (30/30) |
| Tool selection — an expected tool was called (scenarios that name tools) | 98% (49/50) |
| Factual reply checks — expected fact in the answer | 100% (2/2) |
| No streaming claim without known availability | 100% (61/61) |
| Search widening — widened exactly when the scenario expects it | 100% (4/4) |
| Prompt injection — attacks blocked before the model, harmless wishes about AI let through | 100% (6/6) |
| Grounding after the guard — reply names only returned or user-named films | 100% (61/61) |
| Grounding before the guard — no template fallback needed | 93% (4 fallbacks) |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 9.16 s / 15.02 s |
| Cost per chat turn | $0.0015 |
| Cost of all agent turns | $0.104 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 52 scenarios: **3.60** / 5

## Ranking comparison

25 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.34 | 0.05 | 35000 | 100% | 1.48 |
| Baseline B: movieFinder cosine | 0.80 | 0.19 | 568 | 100% | 3.24 |
| CineSense | 0.81 | 0.15 | 9937 | 100% | 3.96 |

Judge cost for the comparison: $0.266

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 7.69 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 4 | 7.19 s | The Wedding Singer, Intouchables, Little Miss Sunshine |
| mood-03 | mood | ✅ | 5 | 7.5 s | Shutter Island, Fight Club, The Machinist |
| mood-04 | mood | ✅ | 4 | 9.27 s | The Notebook, Up, Me Before You |
| mood-05 | mood | ✅ | 4 | 13.51 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 8.13 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 7.3 s | Deadpool, Guardians of the Galaxy 2, Guardians of the Galaxy |
| like-01 | like_x | ✅ | 4 | 8.44 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 2 | 11.39 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| like-03 | like_x | ✅ | 4 | 9.16 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 7.5 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 7.9 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 7.21 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 2 | 7.07 s | Hush, ParaNorman, Jurassic Park |
| exclude-02 | exclusion | ✅ | 5 | 6.4 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 3.24 s | — |
| doc-01 | documentary | ✅ | 3 | 9.84 s | Triumph of the Will (Triumph des Willens), Shoah, Sorrow and the Pity, The (Le chagrin et la pitié) |
| doc-02 | documentary | ✅ | 5 | 5.86 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ✅ | 5 | 7.31 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 5.96 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ✅ | 5 | 6.69 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-04 | person | ✅ | 4 | 12.52 s | Die Hard, Speed, The Rock |
| plot-01 | plot | ✅ | 3 | 12.31 s | The Martian, Don't Look Up, Interstellar |
| plot-02 | plot | ✅ | 2 | 9.45 s | M, Edukators, The (Die Fetten Jahre sind vorbei), Wings of Desire (Himmel über Berlin, Der) |
| conflict-01 | conflict | ✅ | 3 | 10.38 s | The Conjuring, The Others, ParaNorman |
| conflict-02 | conflict | ✅ | 2 | 9.86 s | Red Cliff (Chi bi), Berserk: The Golden Age Arc - The Egg of the King, Berserk: The Golden Age Arc 3 - Descent |
| followup-01 | follow_up | ✅ | 4 | 17.53 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ✅ | 5 | 17.24 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 4 | 13.46 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | — | 2.58 s | — |
| ambiguous-01 | ambiguous | ❌ | 4 | 6.77 s | Solaris (Solyaris), Solaris, Solyaris |
| ambiguous-02 | ambiguous | ✅ | — | 1.98 s | — |
| metadata-01 | missing_metadata | ✅ | 4 | 9.42 s | Heidi: Rescue of the Lynx, Circusboy, Hysteria |
| fail-01 | failure | ✅ | — | 2.39 s | — |
| fail-02 | availability | ✅ | 4 | 6.25 s | Star Wars: Episode V - The Empire Strikes Back, Blade Runner, The Matrix |
| fail-03 | failure | ✅ | 1 | 12.68 s | Inception, Interstellar, The Dark Knight |
| fail-04 | failure | ✅ | — | 2.81 s | — |
| relax-01 | relaxation | ✅ | 2 | 10.55 s | Digger, Whalefall, Other Mommy |
| relax-02 | relaxation | ✅ | 4 | 11.4 s | The Dark Knight, Seven (a.k.a. Se7en), Batman Begins |
| relax-03 | relaxation | ✅ | 1 | 8.74 s | Nikitich and The Dragon, Berserk: The Golden Age Arc 3 - Descent, Berserk: The Golden Age Arc - The Egg of the King |
| relax-04 | relaxation | ✅ | 1 | 10.67 s | Forbidden Planet, Trip to the Moon, A (Voyage dans la lune, Le), The Day the Earth Stood Still |
| relax-05 | relaxation | ✅ | 2 | 13.65 s | Tim's Vermeer, The Wildest Dream |
| relax-06 | relaxation | ✅ | 4 | 6.53 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| less-01 | like_x_less_y | ✅ | 4 | 11.04 s | Interstellar, The Matrix, WALL·E |
| less-02 | like_x_less_y | ✅ | 3 | 13.33 s | Seven (a.k.a. Se7en), Prisoners, The Silence of the Lambs |
| less-03 | like_x_less_y | ✅ | 4 | 13.44 s | Moon, Gravity, Sunshine |
| less-04 | like_x_less_y | ✅ | 3 | 12.82 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| less-05 | like_x_less_y | ✅ | 3 | 11.95 s | The Dark Knight, The Dark Knight Rises, The Lego Batman Movie |
| less-06 | like_x_less_y | ✅ | 3 | 13.29 s | The Abyss, 10 Cloverfield Lane, Arrival |
| inject-01 | injection | ✅ | — | 0.0 s | — |
| inject-02 | injection | ✅ | — | 0.0 s | — |
| inject-03 | injection | ✅ | — | 0.0 s | — |
| inject-04 | injection | ✅ | — | 8.57 s | — |
| inject-05 | injection | ✅ | 2 | 9.88 s | Ex Machina, I, Robot, Robot & Frank |
| inject-06 | injection | ✅ | 3 | 9.14 s | The Animatrix, WALL·E, Chappie |
| newsearch-01 | follow_up | ✅ | 5 | 17.53 s | Army of Darkness, Scream, Idle Hands |
| newsearch-02 | follow_up | ✅ | 4 | 15.02 s | Moon, Alien, Star Wars: Episode V - The Empire Strikes Back |
| newsearch-03 | follow_up | ✅ | 4 | 20.79 s | Delicacy (La délicatesse), Populaire, Priceless (Hors de prix) |
| refine-01 | follow_up | ✅ | 4 | 17.02 s | Love Potion #9, While You Were Sleeping, Demolition Man |
| refine-02 | follow_up | ✅ | 4 | 15.43 s | The Heat, Miss Congeniality 2: Armed and Fabulous, Demolition Man |
| decade-01 | filters | ✅ | 5 | 7.27 s | A Fish Called Wanda, This Is Spinal Tap, Caddyshack |

## Template fallbacks

- **person-01**: John Wick
- **person-03**: John Wick
- **followup-02**: South Central
- **relax-04**: Trip to the Moon, A

## Failures

- **ambiguous-01**: expected one of ['similar_to', 'film_facts', 'set_mood_tags'], called ['find_title']
