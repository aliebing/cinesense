# CineSense evaluation — 2026-10-29

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
| Latency per scenario, median / p90 | 7.77 s / 12.0 s |
| Cost per chat turn | $0.0011 |
| Cost of all agent turns | $0.043 |
| Scenarios with missing token usage | 0 |

Caveats: the checks are deliberately narrow — a scenario without a rule for a metric is not counted in it. Tool errors count only exceptions; a degraded source (e.g. embeddings down) still returns a result.

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5 from titles and years only (which likely favours well-known films). Not an automatic metric.

Mean judge score over 31 scenarios: **3.97** / 5

## Ranking comparison

21 scenarios with mood tags. Same criteria (as set by the agent) and the same hard filters for all three rankers; plot and person signals are left out of the comparison because the baselines have none. *Tag relevance* is the weighted mean relevance of the requested tags — CineSense's own ranking objective; *tag cosine* is movieFinder's objective. Each ranker is favoured by its own metric, so read them together with the judge.

| Ranker | Tag relevance@10 | Tag cosine@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.31 | 0.05 | 35000 | 100% | 1.38 |
| Baseline B: movieFinder cosine | 0.79 | 0.20 | 624 | 100% | 3.48 |
| CineSense | 0.85 | 0.17 | 5781 | 100% | 3.95 |

Judge cost for the comparison: $0.180

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 7.53 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 8.12 s | Hunt for the Wilderpeople, Little Miss Sunshine, Intouchables |
| mood-03 | mood | ✅ | 5 | 8.64 s | Shutter Island, The Machinist, Open Your Eyes (Abre los ojos) |
| mood-04 | mood | ✅ | 5 | 7.72 s | Love Story, Me Before You, The Notebook |
| mood-05 | mood | ✅ | 4 | 10.78 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 5 | 7.82 s | Reservoir Dogs, The Usual Suspects, Rififi (Du rififi chez les hommes) |
| mood-07 | mood | ✅ | 5 | 7.02 s | Deadpool, Guardians of the Galaxy 2, Guardians of the Galaxy |
| like-01 | like_x | ✅ | 4 | 8.71 s | Interstellar, Moon, The Martian |
| like-02 | like_x | ✅ | 4 | 11.71 s | Amelie (Fabuleux destin d'Amélie Poulain, Le), Chocolat, Romantics Anonymous (Les émotifs anonymes) |
| like-03 | like_x | ✅ | 3 | 8.53 s | Oblivion, Looper, Elysium |
| like-04 | like_x | ✅ | 4 | 7.0 s | Moon, Sunshine, Europa Report |
| runtime-01 | runtime | ✅ | 4 | 6.69 s | Headhunters (Hodejegerne), Dead Calm, Anything for Her (Pour elle) |
| runtime-02 | runtime | ✅ | 5 | 6.38 s | Wallace & Gromit: The Best of Aardman Animation, Bill Burr: Why Do I Do This?, Family Guy Presents: Something, Something, Something, Dark Side |
| exclude-01 | exclusion | ✅ | 2 | 7.62 s | Hush, ParaNorman, Cape Fear |
| exclude-02 | exclusion | ✅ | 4 | 8.02 s | The Shawshank Redemption, Planet Earth, Band of Brothers |
| exclude-03 | exclusion | ✅ | — | 3.12 s | — |
| doc-01 | documentary | ✅ | 3 | 7.7 s | Triumph of the Will (Triumph des Willens), Sorrow and the Pity, The (Le chagrin et la pitié), The Rape of Europa |
| doc-02 | documentary | ✅ | 5 | 5.56 s | Planet Earth, Planet Earth II, Wild China |
| person-01 | person | ✅ | 5 | 7.72 s | The Matrix, Much Ado About Nothing, John Wick |
| person-02 | person | ✅ | 5 | 5.77 s | The Dark Knight, Inception, Interstellar |
| person-03 | person | ✅ | 5 | 8.64 s | The Matrix, Much Ado About Nothing, John Wick |
| plot-01 | plot | ✅ | 3 | 9.15 s | The Martian, Pandorum, Planet of the Apes |
| plot-02 | plot | ✅ | 2 | 8.34 s | M, Antibodies (Antikörper), What to Do in Case of Fire (Was tun, wenn's brennt?) |
| conflict-01 | conflict | ✅ | 3 | 12.19 s | The Conjuring, The Haunting, The Others |
| conflict-02 | conflict | ✅ | 3 | 10.69 s | Red Cliff (Chi bi), Band of Brothers, Berserk: The Golden Age Arc - The Egg of the King |
| followup-01 | follow_up | ✅ | 4 | 14.17 s | Alien, Moon, Sunshine |
| followup-02 | follow_up | ✅ | 5 | 14.37 s | Peculiarities of the National Fishing (Osobennosti natsionalnoy rybalki), Friday, Black Sheep |
| followup-03 | follow_up | ✅ | 5 | 13.31 s | Catch Me If You Can, Bridge of Spies, Captain Phillips |
| facts-01 | facts | ✅ | — | 4.01 s | — |
| ambiguous-01 | ambiguous | ✅ | 4 | 9.41 s | Moon, Interstellar, Sunshine |
| ambiguous-02 | ambiguous | ✅ | — | 1.81 s | — |
| metadata-01 | missing_metadata | ✅ | 4 | 5.64 s | Fatherland, Gentle Monster |
| fail-01 | failure | ✅ | — | 2.39 s | — |
| fail-02 | availability | ✅ | 4 | 6.56 s | Star Wars: Episode V - The Empire Strikes Back, Blade Runner, Dark City |
| fail-03 | failure | ✅ | 1 | 12.0 s | The Adjustment Bureau, Passengers, Frequencies |
| fail-04 | failure | ✅ | — | 4.26 s | — |

## Template fallbacks

- **mood-02**: Waking Ned Devine
- **mood-03**: Brooklyn Bridge
- **mood-05**: King Richard
- **runtime-02**: The Empire Strikes Back
- **followup-02**: South Central

## Failures

None.
