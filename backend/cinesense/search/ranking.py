"""Combine whichever search signals are active into one explainable ranking."""

import math
from dataclasses import dataclass, field

from cinesense.core.criteria import SearchCriteria
from cinesense.core.models import Movie, RankedMovie
from cinesense.search.rating import DEFAULT_PRIOR_MEAN, bayesian_rating, catalogue_rating

WEIGHTS = {"tags": 0.4, "plot": 0.3, "people": 0.2, "profile": 0.15, "rating": 0.1, "popularity": 0.08, "recency": 0.04}
RECENCY_FROM, RECENCY_TO = 1970, 2025  # a small bonus growing from 1970 to the newest films
POPULARITY_FULL = 100_000  # MovieLens ratings at which a film counts as fully known (log scale)
TASTE_REASON = 0.75  # normalised profile match from which "fits your taste" is shown
REASON_MIN = 0.3  # tag relevance from which a mood counts as present (shown as a reason)


@dataclass
class Signals:
    tags: dict[str, float] | None = None  # film id -> cosine similarity (raw)
    plot: dict[str, tuple[float, str]] | None = None  # film id -> (similarity, best chunk)
    person: dict[str, float] | None = None  # film id -> name similarity 0..1
    title: dict[str, float] | None = None  # film id -> title similarity 0..1
    tag_relevance: dict[str, dict[int, float]] = field(default_factory=dict)  # for reasons
    tag_names: dict[int, str] = field(default_factory=dict)
    person_names: dict[str, str] = field(default_factory=dict)
    profile: dict[str, float] | None = None  # film id -> taste match (raw)
    disliked: set[str] = field(default_factory=set)  # 👎 films: hidden and counted
    hidden_by_tag: dict[int, int] = field(default_factory=dict)  # not-tag idx -> films it hid (where counted)
    excluded_people: dict[str, str] = field(default_factory=dict)  # film id -> the excluded name that hides it


@dataclass
class CombinedResult:
    items: list[RankedMovie]
    total: int
    hidden_by_exclusion: int
    extended_used: bool = False
    corrected_person: str | None = None  # the name a misspelt person search found (autocorrect)
    corrected_title: str | None = None
    hidden_by: dict[str, int] = field(default_factory=dict)  # "genre:Horror" / "tag:284" -> films it hid here
    total_capped: bool = False  # the mood search kept only its best films: total is a lower bound ("500+")


def _normalised(values: dict[str, float]) -> dict[str, float]:
    best = max(values.values(), default=0.0)
    return {k: (v / best if best > 0 else 0.0) for k, v in values.items()}


def _passes(m: Movie, c: SearchCriteria) -> bool:
    if c.world_id and c.world_id not in m.world_ids:
        return False
    if c.kind != "any" and m.kind != c.kind:
        return False
    if c.original_language and m.original_language != c.original_language:
        return False
    if c.max_runtime_min and m.runtime_min and m.runtime_min > c.max_runtime_min:
        return False
    if c.year_from and (m.year is None or m.year < c.year_from):
        return False
    if c.year_to and (m.year is None or m.year > c.year_to):
        return False
    if c.availability == "cinema" and not m.availability.in_cinema_de:
        return False
    if (
        c.availability == "stream"
        and m.availability.streaming_de is not None
        and not m.availability.streams_on(c.streaming_services)
    ):
        return False  # unknown availability stays in; the API resolves it for the top results
    if c.min_rating is not None and catalogue_rating(m.ml_rating, m.ml_rating_count) < c.min_rating:
        return False
    return m.ml_rating_count >= c.min_rating_count


def combined_rank(
    movies: list[Movie],
    criteria: SearchCriteria,
    signals: Signals,
    hidden_by_tags: int = 0,
    offset: int = 0,
    limit: int = 20,
) -> CombinedResult:
    excluded = {g.lower() for g in criteria.exclude_genres}
    hidden = hidden_by_tags
    # what each exclusion hides in this search, so the UI can say "hides nothing here" (no horror with this actor)
    hidden_by = {f"tag:{t}": n for t, n in signals.hidden_by_tag.items()}
    hidden_by |= {f"genre:{g}": 0 for g in criteria.exclude_genres}
    hidden_by |= {f"person:{q}": 0 for q in criteria.exclude_people}
    kept: list[Movie] = []
    for m in movies:
        genres = {g.lower() for g in m.genres}
        if m.id not in signals.disliked and (q := signals.excluded_people.get(m.id)) is not None:
            hidden += 1
            hidden_by[f"person:{q}"] += 1
            continue
        if m.id in signals.disliked or (excluded and genres & excluded):
            hidden += 1
            for g in criteria.exclude_genres:
                if g.lower() in genres:
                    hidden_by[f"genre:{g}"] += 1
            continue
        if _passes(m, criteria):
            kept.append(m)

    active: dict[str, dict[str, float]] = {}
    if signals.tags is not None:
        # absolute (weighted mean relevance, 0..1), not relative to the best hit: a film that is only 30% funny
        # must not show as a full mood match just because nothing in the results is funnier
        active["tags"] = {k: min(max(v, 0.0), 1.0) for k, v in signals.tags.items()}
    if signals.plot is not None:
        active["plot"] = _normalised({k: v[0] for k, v in signals.plot.items()})
    if signals.title is not None:
        active["people"] = dict(signals.title)
    # a wanted person is a filter, not points: every film here has them, so points would only lift films that miss
    # the mood ("Stallone + funny" showed Rambo). Their part scales the match instead: lead 1.0, cameo 0.5, relative
    # to the best part found (a misspelt name, found at a lower similarity, does not lower every match).
    part: dict[str, float] = {}
    if signals.person:
        best = max(signals.person.values())
        part = {k: v / best for k, v in signals.person.items()} if best > 0 else {}
    taste = _normalised(signals.profile) if signals.profile else {}  # once, not per film
    if taste:
        active["profile"] = taste
    rated = [m.ml_rating for m in kept if m.ml_rating is not None]
    prior = sum(rated) / len(rated) if rated else DEFAULT_PRIOR_MEAN
    # a film asked for by name: no bonus for newer films (that is for browsing moods), the closer title decides
    recency_w = 0.0 if criteria.title else WEIGHTS["recency"]
    total_w = sum(WEIGHTS[k] for k in active) + WEIGHTS["rating"] + WEIGHTS["popularity"] + recency_w

    ranked = []
    for m in kept:
        parts = {k: vals.get(m.id, 0.0) for k, vals in active.items()}
        rating = bayesian_rating(m.ml_rating, m.ml_rating_count, prior) / 5
        base = sum(WEIGHTS[k] * v for k, v in parts.items()) + WEIGHTS["rating"] * rating
        known = WEIGHTS["popularity"] * _popularity(m.ml_rating_count) + recency_w * _recency(m.year)
        score = (base + known) / total_w * part.get(m.id, 1.0)
        ranked.append(
            RankedMovie(
                movie=m,
                score=score,
                match_percent=max(0, min(100, round(100 * score))),
                reasons=_reasons(m, criteria, signals, taste),
            )
        )
    ranked.sort(key=lambda r: (r.score, r.movie.ml_rating_count), reverse=True)
    return CombinedResult(
        items=ranked[offset : offset + limit], total=len(ranked), hidden_by_exclusion=hidden, hidden_by=hidden_by
    )


def _popularity(count: int) -> float:
    return min(math.log1p(max(count, 0)) / math.log1p(POPULARITY_FULL), 1.0)


def _recency(year: int | None) -> float:
    if year is None:
        return 0.0
    return min(max((year - RECENCY_FROM) / (RECENCY_TO - RECENCY_FROM), 0.0), 1.0)


def streaming_reason(m: Movie, c: SearchCriteria) -> list[str]:
    """"streaming on …", naming the wished-for services first."""
    services = m.availability.subscription_services
    wished = [s for s in services if s in c.streaming_services]
    ordered = wished + [s for s in services if s not in wished]
    return [f"streaming on {', '.join(ordered[:2])}"] if ordered else []


def _reasons(m: Movie, c: SearchCriteria, s: Signals, taste: dict[str, float]) -> list[str]:
    out: list[str] = []
    rel = s.tag_relevance.get(m.id, {})
    for t in c.tags:
        if t.mode != "not" and t.idx in rel and t.idx in s.tag_names and rel[t.idx] >= REASON_MIN:
            out.append(f"{s.tag_names[t.idx]} {round(100 * rel[t.idx])}%")
    if s.plot and m.id in s.plot:
        chunk = s.plot[m.id][1].strip().replace("\n", " ")
        out.append(f"plot: {chunk[:80]}{'…' if len(chunk) > 80 else ''}")
    if s.person and m.id in s.person and m.id in s.person_names:
        out.append(f"with {s.person_names[m.id]}")
    if s.title and m.id in s.title:
        out.append("title match")
    if taste.get(m.id, 0.0) >= TASTE_REASON:
        out.append("fits your taste")
    out.extend(streaming_reason(m, c))
    if m.availability.in_cinema_de:
        out.append("in cinemas")
    return out
