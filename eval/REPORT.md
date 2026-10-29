# CineSense evaluation — 2026-10-29

36 scenarios, 36 passed all automatic checks, 0 errored. Agent model: Claude Haiku 5.5 via OpenRouter.

## Automatic metrics

| Metric | Value |
|---|---|
| Constraint satisfaction (results obey runtime/genre/kind/year/person/availability) | 100% |
| Tool selection (an expected tool was called) | 100% |
| Tool success rate (tool calls without error) | 100% |
| Grounding (reply names only returned or user-named films) | 100% |
| Factual reply checks (expected facts in the answer) | 100% |
| Known-good title among the results (where defined) | 100% |
| Grounding fallbacks (template answer used) | 5 |
| Latency per scenario, median / p90 | 7.75 s / 11.46 s |
| Cost per chat turn | $0.0011 |
| Cost of all agent turns | $0.043 |

## Relevance — LLM judge (Claude Sonnet 5.5)

Subjective: the judge rates the agent's top 5 for each scenario on 1–5. Not an automatic metric.

Mean judge score over 32 scenarios: **3.91** / 5

## Ranking comparison

Same criteria (as set by the agent) and the same hard filters for all three rankers. Tag relevance = mean Tag Genome relevance of the requested tags in the top 10 (automatic). Median rating count = how well-known the picks are. Judge = LLM judge (Claude Sonnet 5.5) on the top 5.

| Ranker | Tag relevance@10 | Median rating count | Constraints OK | LLM judge |
|---|---|---|---|---|
| Baseline A: filters + Bayesian rating | 0.32 | 35000 | 100% | 1.36 |
| Baseline B: movieFinder cosine | 0.78 | 926 | 100% | 3.41 |
| CineSense | 0.85 | 3977 | 100% | 3.82 |

Judge cost for the comparison: $0.188

## Per scenario

| Scenario | Category | Passed | Judge | Latency | Top results |
|---|---|---|---|---|---|
| mood-01 | mood | ✅ | 3 | 7.71 s | Moon, Star Wars: Episode V - The Empire Strikes Back, Sunshine |
| mood-02 | mood | ✅ | 5 | 7.48 s | Hunt for the Wilderpeople, Little Miss Sunshine, Intouchables |
| mood-03 | mood | ✅ | 5 | 8.22 s | Shutter Island, The Machinist, Open Your Eyes (Abre los ojos) |
| mood-04 | mood | ✅ | 5 | 7.81 s | Love Story, Up, The Bridges of Madison County |
| mood-05 | mood | ✅ | 4 | 9.44 s | Braveheart, The Lord of the Rings: The Two Towers, The Lord of the Rings: The Fellowship of the Ring |
| mood-06 | mood | ✅ | 4 | 8.24 s | Reservoir Dogs, The Usual Suspects, Rififi (Du rififi chez les hommes) |
| mood-07 | mood | ✅ | 5 | 7.06 s | Deadpool, Guardians of the Galaxy 2, Guardians of the Galaxy |
| like-01 | like_x | ✅ | 4 | 8.83 s | Interstellar, Moon, The Martian |
| like-02 | like_x | ✅ | 4 | 11.19 s | Amelie (Fabuleux destin d'Amélie Poulain, Le), Midnight in Paris, Romantics Anonymous (Les émotifs anonymes) |
| like-03 | like_x | ✅ | 3 | 8.61 s | Oblivion, Looper, Elysium |
| like-04 | like_x | ✅ | 4 | 8.09 s | Moon, Sunshine, Europa Report |
| runtime-01 | runtime | ✅ | 4 | 5.57 s | Headhunters (Hodejegerne), Dead Calm, Anything for Her (Pour elle) |
| runtime-02 | runtime | ✅ | 5 | 7.6 s | Wallace & Gromit: The Best of Aardman Animation, Bill Burr: Why Do I Do This?, Family Guy Presents: Something, Something, Something, Dark Side |
| exclude-01 | exclusion | ✅ | 2 | 8.56 s | Hush, ParaNorman, Cape Fear |
| exclude-02 | exclusion | ✅ | 4 | 6.34 s | The Shawshank Redemption, Planet Earth, Band of Brothers |
| exclude-03 | exclusion | ✅ | — | 3.21 s | — |
| doc-01 | documentary | ✅ | 3 | 6.36 s | Sorrow and the Pity, The (Le chagrin et la pitié), The Rape of Europa, Triumph of the Will (Triumph des Willens) |
| doc-02 | documentary | ✅ | 5 | 5.03 s | Planet Earth, Planet Earth II, Wild China |
| person-01 | person | ✅ | 5 | 7.39 s | The Matrix, Much Ado About Nothing, John Wick |
| person-02 | person | ✅ | 5 | 5.86 s | The Dark Knight, Inception, Interstellar |
| person-03 | person | ✅ | 5 | 6.57 s | The Matrix, Much Ado About Nothing, John Wick |
| plot-01 | plot | ✅ | 3 | 9.13 s | The Martian, Pandorum, Planet of the Apes |
| plot-02 | plot | ✅ | 2 | 9.24 s | M, Antibodies (Antikörper), What to Do in Case of Fire (Was tun, wenn's brennt?) |
| conflict-01 | conflict | ✅ | 3 | 12.52 s | The Haunting, The Others, The Conjuring |
| conflict-02 | conflict | ✅ | 2 | 11.46 s | Red Cliff (Chi bi), Band of Brothers, Red Cliff Part II (Chi Bi Xia: Jue Zhan Tian Xia) |
| followup-01 | follow_up | ✅ | 4 | 13.77 s | Alien, Moon, Sunshine |
| followup-02 | follow_up | ✅ | 5 | 21.93 s | Peculiarities of the National Fishing (Osobennosti natsionalnoy rybalki), Friday, Black Sheep |
| followup-03 | follow_up | ✅ | 5 | 17.13 s | Catch Me If You Can, Bridge of Spies, Captain Phillips |
| facts-01 | facts | ✅ | — | 2.7 s | — |
| ambiguous-01 | ambiguous | ✅ | 4 | 6.76 s | Moon, Interstellar, Sunshine |
| ambiguous-02 | ambiguous | ✅ | — | 1.78 s | — |
| metadata-01 | missing_metadata | ✅ | 4 | 5.13 s | Fatherland, Gentle Monster |
| fail-01 | failure | ✅ | — | 2.18 s | — |
| fail-02 | failure | ✅ | 4 | 5.72 s | Star Wars: Episode V - The Empire Strikes Back, Blade Runner, Dark City |
| fail-03 | failure | ✅ | 1 | 8.06 s | The Adjustment Bureau, Passengers, TiMER |
| fail-04 | failure | ✅ | 4 | 7.8 s | Toni Erdmann, Requiem, Woman In Berlin, A (Anonyma - Eine Frau in Berlin) |

## Failures

None.
