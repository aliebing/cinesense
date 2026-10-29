"""Combine whichever search signals are active into one explainable ranking."""

from dataclasses import dataclass, field

from cinesense.domain.criteria import SearchCriteria
from cinesense.domain.models import Movie, RankedMovie
from cinesense.recommend.baseline import DEFAULT_PRIOR_MEAN, bayesian_rating

WEIGHTS = {"tags": 0.4, "plot": 0.3, "people": 0.2, "rating": 0.1}


@dataclass
class Signals:
    tags: dict[str, float] | None = None  # film id -> cosine similarity (raw)
    plot: dict[str, tuple[float, str]] | None = None  # film id -> (similarity, best chunk)
    person: dict[str, float] | None = None  # film id -> name similarity 0..1
    title: dict[str, float] | None = None  # film id -> title similarity 0..1
    tag_relevance: dict[str, dict[int, float]] = field(default_factory=dict)  # for reasons
    tag_names: dict[int, str] = field(default_factory=dict)
    person_names: dict[str, str] = field(default_factory=dict)


@dataclass
class CombinedResult:
    items: list[RankedMovie]
    total: int
    hidden_by_exclusion: int
    extended_used: bool = False


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
        and not m.availability.subscription_services
    ):
        return False  # unknown availability stays in; the API resolves it for the top results
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
    kept: list[Movie] = []
    for m in movies:
        if excluded and any(g.lower() in excluded for g in m.genres):
            hidden += 1
            continue
        if _passes(m, criteria):
            kept.append(m)

    active: dict[str, dict[str, float]] = {}
    if signals.tags is not None:
        active["tags"] = _normalised(signals.tags)
    if signals.plot is not None:
        active["plot"] = _normalised({k: v[0] for k, v in signals.plot.items()})
    people = {**(signals.title or {}), **(signals.person or {})}
    if signals.person is not None or signals.title is not None:
        active["people"] = people
    rated = [m.ml_rating for m in kept if m.ml_rating is not None]
    prior = sum(rated) / len(rated) if rated else DEFAULT_PRIOR_MEAN
    total_w = sum(WEIGHTS[k] for k in active) + WEIGHTS["rating"]

    ranked = []
    for m in kept:
        parts = {k: vals.get(m.id, 0.0) for k, vals in active.items()}
        rating = bayesian_rating(m.ml_rating, m.ml_rating_count, prior) / 5
        score = (sum(WEIGHTS[k] * v for k, v in parts.items()) + WEIGHTS["rating"] * rating) / total_w
        ranked.append(
            RankedMovie(
                movie=m,
                score=score,
                match_percent=max(0, min(100, round(100 * score))),
                reasons=_reasons(m, criteria, signals),
            )
        )
    ranked.sort(key=lambda r: (r.score, r.movie.ml_rating_count), reverse=True)
    return CombinedResult(
        items=ranked[offset : offset + limit], total=len(ranked), hidden_by_exclusion=hidden
    )


def _reasons(m: Movie, c: SearchCriteria, s: Signals) -> list[str]:
    out: list[str] = []
    rel = s.tag_relevance.get(m.id, {})
    for t in c.tags:
        if t.mode != "not" and t.idx in rel and t.idx in s.tag_names and rel[t.idx] >= 0.3:
            out.append(f"{s.tag_names[t.idx]} {round(100 * rel[t.idx])}%")
    if s.plot and m.id in s.plot:
        chunk = s.plot[m.id][1].strip().replace("\n", " ")
        out.append(f"plot: {chunk[:80]}{'…' if len(chunk) > 80 else ''}")
    if s.person and m.id in s.person and m.id in s.person_names:
        out.append(f"with {s.person_names[m.id]}")
    if s.title and m.id in s.title:
        out.append("title match")
    if services := m.availability.subscription_services:
        out.append(f"streaming on {', '.join(services[:2])}")
    if m.availability.in_cinema_de:
        out.append("in cinemas")
    return out
