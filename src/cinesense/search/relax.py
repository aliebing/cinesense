"""Widen a search that finds too little: list the constraints that may be loosened (least intrusive first),
probe how many films each option finds, and pick one when the agent does not.

Never loosened: not-tags and excluded genres (the user's hard limits), person, title and kind (the wish's identity)."""

import logging
from dataclasses import dataclass

from cinesense.domain.criteria import SearchCriteria

log = logging.getLogger(__name__)

MIN_RESULTS = 3  # fewer films than this and the search is widened
MAX_OPTIONS = 7
RUNTIME_STEP, RUNTIME_MAX = 30, 400
YEAR_STEP = 10


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
    if c.original_language:
        add("language", "Any original language", original_language=None)
    if c.world_id:
        add("world", "All mood worlds", world_id=None)
    if c.availability != "any":
        label = "Not only in cinemas" if c.availability == "cinema" else "Not only streaming"
        add("availability", label, availability="any")
    return out[:MAX_OPTIONS]


def probe(service, c: SearchCriteria, tag_names: list[str], current: int) -> list[Relaxation]:
    """The options that find more films than `current`, with their counts, in the original order."""
    kept = []
    for opt in relaxation_options(c, tag_names):
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
