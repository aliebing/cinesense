# CineSense evaluation — 2026-11-10

63 scenarios, 59 passed all automatic checks, 0 errored. Agent model: anthropic/claude-haiku-5.5 via OpenRouter. Streaming data comes from the cache only (no API budget spent).

## Automatic metrics

| Metric | Result |
|---|---|
| Constraint satisfaction — scenarios with a runtime/genre/kind/year/person/availability rule | 100% (32/32) |
| Tool selection — an expected tool was called (scenarios that name tools) | 98% (51/52) |
| Factual reply checks — expected fact in the answer | 100% (3/3) |
| No streaming claim without known availability | 100% (63/63) |
| Search widening — widened exactly when the scenario expects it | 100% (4/4) |
| Prompt injection — attacks blocked before the model, harmless wishes about AI let through | 100% (6/6) |
| Grounding after the guard — reply names only returned or user-named films | 95% (60/63) |
| Grounding before the guard — no template fallback needed | 90% (3 fallbacks) |
| Tool calls that raised no error | 100% |
| Latency per scenario, median / p90 | 8.73 s / 15.87 s |
| Cost per chat turn | $0.0016 |
| Cost of all agent turns | $0.118 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 55 scenarios: **3.65** / 5

## Ranking comparison

26 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.35 | 0.05 | 35000 | 100% | 1.54 |
| Baseline B: movieFinder cosine | 0.78 | 0.20 | 639 | 100% | 3.15 |
| CineSense | 0.79 | 0.15 | 10145 | 100% | 3.85 |

Judge cost for the comparison: $0.300

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 8.61 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 8.1 s | The Wedding Singer, Little Miss Sunshine, Intouchables |
| mood-03 | mood | ✅ | 4 | 9.43 s | Fight Club, Inception, The Man from Earth |
| mood-04 | mood | ✅ | 5 | 6.97 s | The Notebook, P.S. I Love You, Me Before You |
| mood-05 | mood | ✅ | 4 | 13.72 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 6.87 s | Reservoir Dogs, The Usual Suspects, Inside Man |
| mood-07 | mood | ✅ | 5 | 12.09 s | Deadpool, Guardians of the Galaxy, Guardians of the Galaxy 2 |
| like-01 | like_x | ✅ | 4 | 7.37 s | Interstellar, The Martian, Moon |
| like-02 | like_x | ✅ | 2 | 9.94 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| like-03 | like_x | ✅ | 4 | 8.5 s | Oblivion, Looper, Ex Machina |
| like-04 | like_x | ✅ | 4 | 8.5 s | Moon, Sunshine, Gravity |
| runtime-01 | runtime | ✅ | 4 | 9.55 s | Headhunters (Hodejegerne), Identity, Dead Calm |
| runtime-02 | runtime | ✅ | 5 | 7.81 s | Wallace & Gromit: The Best of Aardman Animation, Zoolander, Old School |
| exclude-01 | exclusion | ✅ | 2 | 7.48 s | Hush, ParaNorman, Jurassic Park |
| exclude-02 | exclusion | ✅ | 5 | 8.11 s | Inception, Interstellar, The Dark Knight |
| exclude-03 | exclusion | ✅ | — | 3.38 s | — |
| doc-01 | documentary | ✅ | 3 | 8.24 s | Triumph of the Will (Triumph des Willens), The Rape of Europa, Sorrow and the Pity, The (Le chagrin et la pitié) |
| doc-02 | documentary | ✅ | 5 | 6.34 s | Planet Earth, Planet Earth II, Encounters at the End of the World |
| person-01 | person | ❌ | 5 | 8.36 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-02 | person | ✅ | 5 | 6.91 s | Inception, Interstellar, The Dark Knight |
| person-03 | person | ❌ | 5 | 6.25 s | The Matrix, John Wick: Chapter Two, John Wick: Chapter 3 – Parabellum |
| person-04 | person | ✅ | 2 | 12.93 s | The Matrix, The Avengers, Edge of Tomorrow |
| plot-01 | plot | ✅ | 3 | 9.65 s | The Martian, Don't Look Up, Interstellar |
| plot-02 | plot | ✅ | 2 | 7.72 s | M, Edukators, The (Die Fetten Jahre sind vorbei), Wings of Desire (Himmel über Berlin, Der) |
| conflict-01 | conflict | ✅ | 2 | 10.86 s | My Neighbor Totoro (Tonari no Totoro), Edward Scissorhands, Kiki's Delivery Service (Majo no takkyûbin) |
| conflict-02 | conflict | ✅ | 2 | 15.97 s | Band of Brothers, Red Cliff (Chi bi), Red Cliff Part II (Chi Bi Xia: Jue Zhan Tian Xia) |
| followup-01 | follow_up | ✅ | 4 | 15.87 s | Moon, Alien, Sunshine |
| followup-02 | follow_up | ❌ | 5 | 15.64 s | There's Something About Mary, Austin Powers: International Man of Mystery, Office Space |
| followup-03 | follow_up | ✅ | 4 | 17.12 s | Catch Me If You Can, Captain Phillips, Bridge of Spies |
| facts-01 | facts | ✅ | — | 2.26 s | — |
| ambiguous-01 | ambiguous | ❌ | 5 | 8.52 s | Solaris (Solyaris), Solaris, Solyaris |
| ambiguous-02 | ambiguous | ✅ | 5 | 8.3 s | Inception, Interstellar, The Dark Knight |
| metadata-01 | missing_metadata | ✅ | 4 | 10.76 s | Heidi: Rescue of the Lynx, Circusboy, Hysteria |
| fail-01 | failure | ✅ | — | 2.84 s | — |
| fail-02 | availability | ✅ | 4 | 8.73 s | Star Wars: Episode V - The Empire Strikes Back, Moon, Blade Runner |
| fail-03 | failure | ✅ | 2 | 10.98 s | The Adjustment Bureau, Passengers, Her |
| fail-04 | failure | ✅ | — | 3.68 s | — |
| relax-01 | relaxation | ✅ | 2 | 12.54 s | Digger, Possible Love, Whalefall |
| relax-02 | relaxation | ✅ | 4 | 12.19 s | Primetime, The Thing with Feathers, Shame and Money |
| relax-03 | relaxation | ✅ | 2 | 8.11 s | Nikitich and The Dragon, 7 Days in Hell, Teacher of the Year |
| relax-04 | relaxation | ✅ | 1 | 9.94 s | Forbidden Planet, Trip to the Moon, A (Voyage dans la lune, Le), The Day the Earth Stood Still |
| relax-05 | relaxation | ✅ | 2 | 6.75 s | Man on Wire, Becoming Warren Buffett, Hot Coffee |
| relax-06 | relaxation | ✅ | 4 | 5.94 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| less-01 | like_x_less_y | ✅ | 3 | 11.98 s | Interstellar, WALL·E, The Matrix |
| less-02 | like_x_less_y | ✅ | 2 | 16.12 s | Seven (a.k.a. Se7en), Prisoners, The Silence of the Lambs |
| less-03 | like_x_less_y | ✅ | 4 | 12.39 s | Moon, Gravity, Europa Report |
| less-04 | like_x_less_y | ✅ | 3 | 14.54 s | Before Sunset, Midnight in Paris, Amelie (Fabuleux destin d'Amélie Poulain, Le) |
| less-05 | like_x_less_y | ✅ | 3 | 10.75 s | The Lego Batman Movie, The Dark Knight, Batman Begins |
| less-06 | like_x_less_y | ✅ | 3 | 11.78 s | The Abyss, 10 Cloverfield Lane, Arrival |
| inject-01 | injection | ✅ | — | 0.0 s | — |
| inject-02 | injection | ✅ | — | 0.0 s | — |
| inject-03 | injection | ✅ | — | 0.0 s | — |
| inject-04 | injection | ✅ | — | 7.68 s | — |
| inject-05 | injection | ✅ | 3 | 9.67 s | Ex Machina, Blade Runner, I, Robot |
| inject-06 | injection | ✅ | 4 | 10.82 s | The Animatrix, Chappie, WALL·E |
| newsearch-01 | follow_up | ✅ | 5 | 19.02 s | Army of Darkness, Scream, Idle Hands |
| newsearch-02 | follow_up | ✅ | 4 | 15.68 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Alien |
| newsearch-03 | follow_up | ✅ | 4 | 22.64 s | Delicacy (La délicatesse), Populaire, Priceless (Hors de prix) |
| refine-01 | follow_up | ✅ | 4 | 17.82 s | Love Potion #9, While You Were Sleeping, Demolition Man |
| refine-02 | follow_up | ✅ | 4 | 19.26 s | The Heat, Miss Congeniality 2: Armed and Fabulous, Demolition Man |
| decade-01 | filters | ✅ | 5 | 7.39 s | A Fish Called Wanda, This Is Spinal Tap, Caddyshack |
| rating-01 | filters | ✅ | 5 | 9.13 s | Little Miss Sunshine, Intouchables, Crazy, Stupid, Love. |
| rating-02 | conflict | ✅ | 3 | 7.47 s | Crazy, Stupid, Love., When Harry Met Sally..., The Princess Bride |

## Template fallbacks

- **mood-05**: The One
- **refine-01**: The Demolition Man,
- **refine-02**: The Demolition Man,

## Failures

- **person-01**: unlisted title: John Wick
- **person-03**: unlisted title: John Wick
- **followup-02**: unlisted title: South Central
- **ambiguous-01**: expected one of ['similar_to', 'film_info', 'set_mood_tags'], called ['find']
