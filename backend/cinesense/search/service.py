"""Run a SearchCriteria against the catalogue: candidate generation per signal, then combined ranking."""

import asyncio
import logging
import re
import unicodedata
from collections import OrderedDict

import numpy as np

from cinesense.core.criteria import MUST_THRESHOLD, NOT_THRESHOLD, SearchCriteria
from cinesense.search.ranking import CombinedResult, Signals, combined_rank, excluded, passes, streaming_reason

log = logging.getLogger(__name__)
STREAM_CHECK_LIMIT = 30  # streaming API lookups per search (free plan budget); cache hits don't count
SERVICE_SCAN = 300  # films checked when the user names a service: most top films stream elsewhere
TAG_LIMIT = 500  # films a catalogue-wide mood search keeps (its best matches)
EMBED_CACHE_SIZE = 256  # plot-query embeddings kept per service (the chat agent's service lives for the process)


def _norm(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(plain.lower().split())


def correction(query: str | None, found: str | None) -> str | None:
    """The found name as an autocorrect of `query`, or None when the query is already right: it occurs in the
    match ("bullock" in "Sandra Bullock", "lord of the rings" in every part's title), ignoring case and accents.
    MovieLens' alternative title in brackets is dropped ("Amelie (Fabuleux destin …)" -> "Amelie")."""
    if not query or not found:
        return None
    found = re.sub(r"\s*\(.*\)\s*$", "", found).strip() or found
    return None if _norm(query) in _norm(found) else found


def _best(scores: dict[str, float] | None, labels: dict[str, str]) -> str | None:
    if not scores:
        return None
    return labels.get(max(scores, key=scores.get))


class SearchService:
    def __init__(self, provider, streaming=None, embedder=None, live=None, on_import=None) -> None:
        self.provider = provider
        self.streaming = streaming
        self.embedder = embedder
        self.live = live
        self.on_import = on_import  # called with the ids of films just imported live (to enrich them)
        self._embed_cache: OrderedDict[str, list[float]] = OrderedDict()  # probes reuse the search's embedding

    def _embed(self, text: str) -> list[float] | None:
        if self.embedder is None:
            return None
        if text in self._embed_cache:
            self._embed_cache.move_to_end(text)
            return self._embed_cache[text]
        try:
            vec = asyncio.run(self.embedder.embed([text]))[0]
        except Exception as exc:  # noqa: BLE001 — degrade to no plot signal; a failure is not cached (retry later)
            log.warning("embedding failed: %s", exc)
            return None
        self._embed_cache[text] = vec
        if len(self._embed_cache) > EMBED_CACHE_SIZE:
            self._embed_cache.popitem(last=False)
        return vec

    def can_embed(self, text: str) -> bool:
        """Whether a plot search for this text would really search plots (embeddings configured and working)."""
        return self._embed(text) is not None

    def count(self, c: SearchCriteria) -> int:
        """How many films a search would rank — a cheap probe: no live import, no streaming lookups, no profile."""
        return self._candidates(c, None, offset=0, allow_live=False)[0].total

    def run(self, c: SearchCriteria, offset: int = 0, limit: int = 20, profile=None) -> CombinedResult:
        result, sig, extended_used = self._candidates(c, profile, offset, allow_live=True)
        p = self.provider
        # a stream filter may drop films that turn out not to stream: rank a few spare ones to fill the page
        window = limit
        if c.availability == "stream" and self.streaming is not None:
            window += SERVICE_SCAN if c.streaming_services else STREAM_CHECK_LIMIT
        if c.has_tags():
            top_ids = [r.movie.id for r in result.items[: offset + window]]
            vectors = p.tag_vectors(top_ids)
            idxs = [t.idx for t in c.tags]
            sig.tag_relevance = {fid: {i: float(vectors[row][i]) for i in idxs} for row, fid in enumerate(top_ids)}
        page = combined_rank([r.movie for r in result.items], c, sig, hidden_by_tags=0, offset=offset, limit=window)
        page.hidden_by_exclusion = result.hidden_by_exclusion
        page.hidden_by = result.hidden_by
        page.total_capped = result.total_capped
        for r in page.items:  # callers fill images/streaming on the page; never mutate the shared catalogue
            r.movie = r.movie.model_copy(deep=True)
        page.extended_used = extended_used
        if offset == 0:  # autocorrect for the advanced search: the name that was really found
            page.corrected_person = correction(c.person, _best(sig.person, sig.person_names))
            titles = {r.movie.id: r.movie.title for r in result.items}
            page.corrected_title = correction(c.title, _best(sig.title, titles))
        if c.availability == "stream":
            page = self._resolve_streaming(page, limit, c)
        page.items = page.items[:limit]
        return page

    def _candidates(self, c: SearchCriteria, profile, offset: int, allow_live: bool):
        """Candidate generation per signal and the first ranking over all candidates."""
        p = self.provider
        sig = Signals(tag_names=dict(enumerate(p.list_tags())) if c.has_tags() else {})
        restrict: set[str] | None = None
        hidden = 0
        capped = False
        # only exclusions ("no horror") next to a text search: filter its hits, do not replace them with the
        # catalogue's best-known films (a tag search without weights)
        exclusions_only = c.has_tags() and not c.prefer_weights() and c.has_text_signal()
        # a person, a title or a told story picks the films; mood tags then only rank them (prefer) or narrow them
        # (must / not). The catalogue-wide tag search would keep just its top 500 and lose e.g. "Speed" for action +
        # funny, or every Berlin film for "a heist in Berlin". Without embeddings the story finds nothing: tags search.
        plot_vec = self._embed(c.plot_query) if c.plot_query else None
        tags_on_identity = c.has_tags() and bool(c.person or c.title or plot_vec is not None)
        tags_filter_hits = exclusions_only or tags_on_identity

        for q in c.exclude_people:  # "without Stallone": in any role, a misspelt name found like a wanted one
            for film_id in p.search_person(q, "any")[0]:
                sig.excluded_people.setdefault(film_id, q)
        if profile is not None:
            sig.disliked = set(profile.disliked)
        if c.has_tags() and not tags_filter_hits:
            sig.tags, hidden, capped = _best_by_tags(p, c, sig)
            restrict = set(sig.tags)
        if c.person:
            sig.person, sig.person_names = p.search_person(c.person, c.person_role)
            restrict = set(sig.person) if restrict is None else restrict & set(sig.person)
        if c.title:
            sig.title = p.search_title(c.title)
            restrict = set(sig.title) if restrict is None else restrict & set(sig.title)
        if (vec := plot_vec) is not None:
            # few cinema films would rarely reach the catalogue-wide top 150: rank plots among them only
            only = (
                [m.id for m in p.list_movies() if m.availability.in_cinema_de] if c.availability == "cinema" else None
            )
            hits = p.semantic_search(vec, k=150, only_ids=only) if only is not None else p.semantic_search(vec, k=150)
            sig.plot = {m.id: (s, chunk) for m, s, chunk in hits}
            if restrict is None:
                restrict = set(sig.plot)
            elif not (c.has_tags() or c.person or c.title):
                restrict |= set(sig.plot)

        if tags_filter_hits and restrict:
            restrict, sig.hidden_by_tag, sig.tags = _tags_on_hits(p, c, restrict)
            hidden += sum(sig.hidden_by_tag.values())

        if profile is not None and profile.taste:
            sig.profile = _taste_scores(p, profile)
        movies = p.list_movies()
        if restrict is not None:
            movies = [m for m in movies if m.id in restrict]
        extended_used = False
        # live search only on the first page (later pages reuse the lazily imported films)
        wants_live = (c.title or c.person) and (c.extended or len(movies) < 5)
        if allow_live and self.live is not None and offset == 0 and wants_live:
            live_hits = self._live(c, sig)
            if live_hits:
                extended_used = True
                known = {m.id for m in movies}
                imdb_known = {m.imdb_id for m in p.list_movies() if m.imdb_id}
                fresh = [m for m in live_hits if m.id not in known and m.imdb_id not in imdb_known]
                if fresh and hasattr(p, "upsert_live"):
                    p.upsert_live(fresh)  # lazy import; German title, plots and embeddings follow in the background
                    if self.on_import is not None:
                        self.on_import([m.id for m in fresh])
                movies += fresh
        if c.title and sig.title:
            sig.title = _without_sound_alikes(sig.title)
            movies = [m for m in movies if m.id in sig.title]
        if c.person and sig.person:  # every filter holds together, also for films the live search added
            movies = [m for m in movies if m.id in sig.person]
        result = combined_rank(movies, c, sig, hidden_by_tags=hidden, offset=0, limit=len(movies) or 1)
        result.total_capped = capped
        return result, sig, extended_used

    def _live(self, c: SearchCriteria, sig: Signals) -> list:
        hits = []
        if c.title:
            found = self.live.search_title(c.title)
            known = sig.title or {}
            sig.title = {**known, **{m.id: max(0.8, known.get(m.id, 0.0)) for m in found}}  # never lower a match
            hits += found
        if c.person:
            name, found = self.live.search_person(c.person)
            sig.person = {**(sig.person or {}), **{m.id: 0.9 for m in found}}
            sig.person_names = {**sig.person_names, **{m.id: name for m in found if name}}
            hits += found
        return hits

    def _resolve_streaming(self, page: CombinedResult, limit: int, c: SearchCriteria) -> CombinedResult:
        """Look up candidates in rank order until `limit` of them may stream; at most STREAM_CHECK_LIMIT API lookups
        (cached answers are free)."""
        if self.streaming is None:
            return page
        cached = getattr(self.streaming, "cached_de", None)
        kept, dropped, lookups, rest = [], 0, 0, list(page.items)
        while rest and len(kept) < limit:
            r = rest.pop(0)
            m = r.movie
            if m.imdb_id and m.availability.streaming_de is None:
                m.availability.streaming_de = cached(m.imdb_id) if cached else None
                if m.availability.streaming_de is None:
                    if lookups >= STREAM_CHECK_LIMIT:
                        rest.insert(0, r)
                        break
                    m.availability.streaming_de = self.streaming.get_de(m.imdb_id)
                    lookups += 1
                if not any(x.startswith("streaming on") for x in r.reasons):
                    r.reasons.extend(streaming_reason(m, c))  # the explanation may only claim what reasons say
            if m.availability.streaming_de is None or m.availability.streams_on(c.streaming_services):
                kept.append(r)  # unknown stays (labelled in the UI); known-not-streaming drops out
            else:
                dropped += 1
        if c.streaming_services:  # the user named a service: confirmed films before unknown ones
            kept.sort(key=lambda r: r.movie.availability.streaming_de is None)
        page.items = kept + rest
        page.total = max(page.total - dropped, len(page.items))
        return page


def _best_by_tags(p, c: SearchCriteria, sig: Signals) -> tuple[dict[str, float], int, bool]:
    """A mood search over the whole catalogue: its TAG_LIMIT best films among those the hard filters and exclusions
    leave, so "horror + funny, from 2003" ranks the best films from 2003, not the films from 2003 among the best of
    all years. Filtered films never reach Postgres' limit; excluded ones (👎, genre, person) are fetched on top and
    kept where they rank above the last film kept, so the ranking can count what each exclusion hid here.
    Returns (film id -> tag score, films hidden by not-tags, whether the limit was reached)."""
    movies = p.list_movies()
    blocked = {m.id for m in movies if not passes(m, c)}
    out = {m.id for m in movies if m.id not in blocked and excluded(m, c, sig)}
    scope: dict = {}
    if blocked:  # whichever list is shorter (a year filter can block most of the catalogue)
        if len(blocked) > len(movies) // 2:
            scope["only_ids"] = [m.id for m in movies if m.id not in blocked]
        else:
            scope["skip_ids"] = sorted(blocked)
    hits, hidden = p.tag_search(
        c.prefer_weights(),
        c.must_tags(),
        c.not_tags(),
        MUST_THRESHOLD,
        NOT_THRESHOLD,
        limit=TAG_LIMIT + len(out),
        **scope,
    )
    kept, n = {}, 0
    for film_id, score in hits:
        if n >= TAG_LIMIT:
            break
        kept[film_id] = score
        n += film_id not in out
    return kept, hidden, n >= TAG_LIMIT


def _tags_on_hits(p, c: SearchCriteria, hits: set[str]) -> tuple[set[str], dict[int, int], dict[str, float] | None]:
    """Mood tags applied to films a text signal found: not-tags hide (counted per tag), must-tags narrow, prefer
    and must weights give the tag score for ranking. A film without Tag Genome data (NaN) is never hidden by a not-tag,
    cannot prove a must-tag, and scores 0."""
    ids = sorted(hits)
    vectors = p.tag_vectors(ids)
    hides = {t: {fid for row, fid in enumerate(ids) if vectors[row][t] >= NOT_THRESHOLD} for t in c.not_tags()}
    excluded = set().union(*hides.values())
    lacking = {fid for row, fid in enumerate(ids) if not all(vectors[row][t] >= MUST_THRESHOLD for t in c.must_tags())}
    kept = hits - excluded - lacking
    weights = c.prefer_weights()
    scores = None
    if weights:
        total = sum(weights.values())
        rows = {fid: row for row, fid in enumerate(ids)}
        scores = {
            fid: sum(w / total * float(np.nan_to_num(vectors[rows[fid]][t])) for t, w in weights.items())
            for fid in kept
        }
    return kept, {t: len(f) for t, f in hides.items()}, scores


_taste_cache: dict[tuple, dict[str, float] | None] = {}


STRONG_TITLE, WEAK_TITLE = 0.8, 0.7


def _without_sound_alikes(scores: dict[str, float]) -> dict[str, float]:
    """When some titles really match ("Winnetou 1. Teil" contains "Winnetou"), titles that only sound alike
    ("Win Win", "Wind") are noise. Without a strong match they stay: a typo must still find the film."""
    if max(scores.values()) < STRONG_TITLE:
        return scores
    return {k: v for k, v in scores.items() if v >= WEAK_TITLE}


def _taste_scores(provider, profile) -> dict[str, float] | None:
    """Taste match per film, cached per profile (a full tag search over the catalogue otherwise runs on every
    personalised request). Scaled against the best film not rated yet: liked films would dwarf everything."""
    key = (id(provider), tuple(sorted(profile.taste.items())), tuple(sorted(profile.liked)))
    if key not in _taste_cache:
        hits = dict(provider.tag_search(profile.taste, [], [], MUST_THRESHOLD, NOT_THRESHOLD, limit=3000)[0])
        best = max((v for k, v in hits.items() if k not in profile.liked), default=0.0)
        if len(_taste_cache) > 256:
            _taste_cache.clear()
        _taste_cache[key] = {k: min(1.0, v / best) for k, v in hits.items()} if best > 0 else None
    return _taste_cache[key]
