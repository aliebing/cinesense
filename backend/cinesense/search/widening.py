"""Widen a search that finds too little: list the constraints that may be loosened (least intrusive first),
probe how many films each option finds, and pick one when the agent does not.

Never loosened: not-tags, excluded genres and people (the user's hard limits), person, title and kind (the wish's
identity)."""

import logging
from dataclasses import dataclass

from cinesense.core.criteria import MUST_THRESHOLD, SearchCriteria
from cinesense.core.models import Movie
from cinesense.search.ranking import REASON_MIN
from cinesense.search.rating import DEFAULT_PRIOR_MEAN, catalogue_rating

log = logging.getLogger(__name__)

MIN_RESULTS = 3  # fewer films than this and the search is widened
MAX_OPTIONS = 8
RUNTIME_STEP, RUNTIME_MAX = 30, 400
YEAR_STEP = 10
RATING_STEP = 0.3  # below the catalogue mean a rating filter is dropped, not lowered


@dataclass
class Relaxation:
    id: str
    label: str
    criteria: SearchCriteria
    count: int = 0


def _name(tag_names: list[str], idx: int) -> str:
    return tag_names[idx] if idx < len(tag_names) else str(idx)


def relaxation_options(c: SearchCriteria, tag_names: list[str]) -> list[Relaxation]:
    out: list[Relaxation] = []

    def add(id_: str, label: str, **update) -> None:
        out.append(Relaxation(id_, label, c.model_copy(update=update, deep=True)))

    for t in c.tags:
        if t.mode == "must":
            tags = [x.model_copy(update={"mode": "prefer"}) if x.idx == t.idx else x for x in c.tags]
            add(f"must-to-prefer:{t.idx}", f"'{_name(tag_names, t.idx)}' as a preference, not a must", tags=tags)
    mood = [t for t in c.tags if t.mode != "not"]
    if mood and not c.plot_query:
        names = ", ".join(_name(tag_names, t.idx) for t in mood)
        add(
            "tags-to-plot",
            f"Search the mood ({names}) in plot descriptions",
            tags=[t for t in c.tags if t.mode == "not"],
            plot_query=names,
        )
    if c.max_runtime_min:
        n = min(RUNTIME_MAX, c.max_runtime_min + RUNTIME_STEP)
        add("runtime", f"Allow up to {n} min", max_runtime_min=n)
    if c.year_from or c.year_to:
        lo = c.year_from - YEAR_STEP if c.year_from else None
        hi = c.year_to + YEAR_STEP if c.year_to else None
        add("years", f"Widen the years to {lo or '…'}–{hi or '…'}", year_from=lo, year_to=hi)
    if c.min_rating is not None:
        r = round(c.min_rating - RATING_STEP, 1)
        if r >= DEFAULT_PRIOR_MEAN:
            add("rating", f"Rated {r} or better", min_rating=r)
        else:
            add("rating", "Any rating", min_rating=None)
    if c.original_language:
        add("language", "Any original language", original_language=None)
    if c.world_id:
        add("world", "All mood worlds", world_id=None)
    if c.streaming_services:
        add("services", "Any streaming service", streaming_services=[])
    if c.availability != "any":
        label = "Not only in cinemas" if c.availability == "cinema" else "Not only streaming"
        add("availability", label, availability="any", streaming_services=[])
    return out[:MAX_OPTIONS]


def probe(service, c: SearchCriteria, tag_names: list[str], current: int) -> list[Relaxation]:
    """The options that find more films than `current`, with their counts, in the original order."""
    kept = []
    for opt in relaxation_options(c, tag_names):
        can_embed = getattr(service, "can_embed", None)
        if opt.id == "tags-to-plot" and can_embed is not None and not can_embed(opt.criteria.plot_query):
            continue  # without embeddings the "plot search" would silently drop the mood
        try:
            opt.count = service.count(opt.criteria)
        except Exception as exc:  # noqa: BLE001 — an option we cannot count is not offered
            log.warning("relaxation probe %s failed: %s", opt.id, exc)
            continue
        if opt.count > current:
            kept.append(opt)
    return kept


def pick_auto(options: list[Relaxation]) -> Relaxation | None:
    """The least intrusive option that finds enough films, else the one that finds the most."""
    enough = [o for o in options if o.count >= MIN_RESULTS]
    if enough:
        return enough[0]
    return max(options, key=lambda o: o.count, default=None)


def apply(c: SearchCriteria, option_id: str, tag_names: list[str]) -> Relaxation | None:
    return next((o for o in relaxation_options(c, tag_names) if o.id == option_id), None)


def misses(
    movie: Movie, original: SearchCriteria, tag_names: list[str], tag_relevance: dict[int, float] | None = None
) -> list[str]:
    """What part of the original wish a film from a widened search does not meet — only the relaxable fields
    (exclusions are never widened, so a film never misses them). Unknown values are not reported as misses."""
    out = []
    if original.max_runtime_min and movie.runtime_min and movie.runtime_min > original.max_runtime_min:
        out.append(f"{movie.runtime_min} min, longer than {original.max_runtime_min}")
    lo, hi = original.year_from, original.year_to
    if movie.year and ((lo and movie.year < lo) or (hi and movie.year > hi)):
        out.append(f"from {movie.year}, outside {lo or '…'}–{hi or '…'}")
    if original.min_rating is not None:
        rating = catalogue_rating(movie.ml_rating, movie.ml_rating_count)
        if rating < original.min_rating:
            out.append(f"rated {rating:.1f}, below {original.min_rating}")
    if original.original_language and movie.original_language and movie.original_language != original.original_language:
        out.append(f"original language {movie.original_language}, not {original.original_language}")
    if original.world_id and original.world_id not in movie.world_ids:
        out.append("outside this mood world")
    a = movie.availability
    if original.availability == "cinema" and not a.in_cinema_de:
        out.append("not in cinemas")
    if original.availability == "stream" and not a.subscription_services:
        out.append("streaming not confirmed")
    elif original.streaming_services and not a.streams_on(original.streaming_services):
        out.append(f"not on {' or '.join(original.streaming_services)}")
    relevance = tag_relevance or {}
    for t in original.tags:
        if t.mode == "not":
            continue
        name = _name(tag_names, t.idx)
        value = relevance.get(t.idx)
        if value is None or value != value:  # NaN: the film has no Tag Genome vector
            out.append(f"no mood data for '{name}'")
        elif t.mode == "must" and value < MUST_THRESHOLD:
            out.append(f"little '{name}'")  # a weak preference only ranks lower, it is no miss
    return out


def applied_update(state: dict, opt: Relaxation) -> dict:
    """Agent state update for an applied relaxation; the first one keeps the criteria it widened."""
    return {
        "criteria": opt.criteria.model_dump(),
        "criteria_changed": True,
        "relaxed": [*(state.get("relaxed") or []), opt.label],
        "relax_options": [],
        "original_criteria": state.get("original_criteria") or state.get("criteria"),
    }


def mark_misses(items: list, original: SearchCriteria, provider) -> None:
    """Fill RankedMovie.misses against the original criteria (in place)."""
    wanted = [t.idx for t in original.tags if t.mode != "not"]
    vectors = provider.tag_vectors([r.movie.id for r in items]) if wanted and items else None
    for row, r in enumerate(items):
        relevance = {i: float(vectors[row][i]) for i in wanted} if vectors is not None else None
        r.misses = misses(r.movie, original, provider.list_tags(), relevance)


@dataclass
class MoodCoverage:
    missing: list[str]  # wanted moods none of the films shows
    combined: bool  # some film shows every wanted mood


def mood_coverage(items: list, c: SearchCriteria, provider) -> MoodCoverage:
    """How far the top films meet the wanted moods (relevance >= REASON_MIN counts as present). "Romantic, funny and
    a bit scary" may rank romantic comedies first: named so the reply says so instead of quietly meeting two of
    three, and "funny and scary" may split into comedies and thrillers with no film that is both."""
    wanted = [t.idx for t in c.tags if t.mode != "not"]
    if not wanted or not items:
        return MoodCoverage([], True)
    vectors = provider.tag_vectors([r.movie.id for r in items])
    names = provider.list_tags()

    def present(row, i) -> bool:
        return row[i] == row[i] and float(row[i]) >= REASON_MIN  # NaN: no mood data

    missing = [_name(names, i) for i in wanted if not any(present(row, i) for row in vectors)]
    combined = any(all(present(row, i) for i in wanted) for row in vectors)
    return MoodCoverage(missing, combined)
