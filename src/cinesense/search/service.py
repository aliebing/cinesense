"""Run a SearchCriteria against the catalogue: candidate generation per signal, then combined ranking."""

import asyncio
import logging

from cinesense.domain.criteria import MUST_THRESHOLD, NOT_THRESHOLD, SearchCriteria
from cinesense.recommend.combined import CombinedResult, Signals, combined_rank

log = logging.getLogger(__name__)
STREAM_CHECK_LIMIT = 30  # streaming lookups per search (free plan budget)


class SearchService:
    def __init__(self, provider, streaming=None, embedder=None, live=None, on_import=None) -> None:
        self.provider = provider
        self.streaming = streaming
        self.embedder = embedder
        self.live = live
        self.on_import = on_import  # called with the ids of films just imported live (to enrich them)
        self._embed_cache: dict[str, list[float] | None] = {}  # one embedding per text (probes reuse it)

    def _embed(self, text: str) -> list[float] | None:
        if self.embedder is None:
            return None
        if text not in self._embed_cache:
            try:
                self._embed_cache[text] = asyncio.run(self.embedder.embed([text]))[0]
            except Exception as exc:  # noqa: BLE001 — degrade to no plot signal
                log.warning("embedding failed: %s", exc)
                self._embed_cache[text] = None
        return self._embed_cache[text]

    def count(self, c: SearchCriteria) -> int:
        """How many films a search would rank — a cheap probe: no live import, no streaming lookups, no profile."""
        return self._candidates(c, None, offset=0, allow_live=False)[0].total

    def run(self, c: SearchCriteria, offset: int = 0, limit: int = 20, profile=None) -> CombinedResult:
        result, sig, extended_used = self._candidates(c, profile, offset, allow_live=True)
        p = self.provider
        # a stream filter may drop films that turn out not to stream: rank a few spare ones to fill the page
        window = limit + STREAM_CHECK_LIMIT if c.availability == "stream" and self.streaming is not None else limit
        if c.has_tags():
            top_ids = [r.movie.id for r in result.items[: offset + window]]
            vectors = p.tag_vectors(top_ids)
            idxs = [t.idx for t in c.tags]
            sig.tag_relevance = {fid: {i: float(vectors[row][i]) for i in idxs} for row, fid in enumerate(top_ids)}
        page = combined_rank([r.movie for r in result.items], c, sig, hidden_by_tags=0, offset=offset, limit=window)
        page.hidden_by_exclusion = result.hidden_by_exclusion
        for r in page.items:  # callers fill images/streaming on the page; never mutate the shared catalogue
            r.movie = r.movie.model_copy(deep=True)
        page.extended_used = extended_used
        if c.availability == "stream":
            page = self._resolve_streaming(page, limit)
        page.items = page.items[:limit]
        return page

    def _candidates(self, c: SearchCriteria, profile, offset: int, allow_live: bool):
        """Candidate generation per signal and the first ranking over all candidates."""
        p = self.provider
        sig = Signals(tag_names=dict(enumerate(p.list_tags())) if c.has_tags() else {})
        restrict: set[str] | None = None
        hidden = 0

        if c.has_tags():
            hits, hidden = p.tag_search(c.prefer_weights(), c.must_tags(), c.not_tags(), MUST_THRESHOLD, NOT_THRESHOLD)
            sig.tags = dict(hits)
            restrict = set(sig.tags)
        if c.person:
            sig.person, sig.person_names = p.search_person(c.person, c.person_role)
            restrict = set(sig.person) if restrict is None else restrict & set(sig.person)
        if c.title:
            sig.title = p.search_title(c.title)
            restrict = set(sig.title) if restrict is None else restrict & set(sig.title)
        if c.plot_query and (vec := self._embed(c.plot_query)) is not None:
            hits = p.semantic_search(vec, k=150)
            sig.plot = {m.id: (s, chunk) for m, s, chunk in hits}
            if restrict is None:
                restrict = set(sig.plot)
            elif not (c.has_tags() or c.person or c.title):
                restrict |= set(sig.plot)

        if profile is not None:
            sig.disliked = set(profile.disliked)
            if profile.taste:
                sig.profile = _taste_scores(p, profile)
        movies = p.list_movies()
        if restrict is not None:
            movies = [m for m in movies if m.id in restrict]
        extended_used = False
        # live search only on the first page (later pages reuse the lazily imported films)
        if allow_live and self.live is not None and offset == 0 and (c.title or c.person) and (c.extended or len(movies) < 5):
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
        result = combined_rank(movies, c, sig, hidden_by_tags=hidden, offset=0, limit=len(movies) or 1)
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

    def _resolve_streaming(self, page: CombinedResult, limit: int) -> CombinedResult:
        """Look up candidates in rank order until `limit` of them may stream; at most STREAM_CHECK_LIMIT lookups."""
        if self.streaming is None:
            return page
        kept, dropped, lookups, rest = [], 0, 0, list(page.items)
        while rest and len(kept) < limit and lookups < STREAM_CHECK_LIMIT:
            r = rest.pop(0)
            m = r.movie
            if m.imdb_id and m.availability.streaming_de is None:
                m.availability.streaming_de = self.streaming.get_de(m.imdb_id)
                lookups += 1
            if m.availability.streaming_de is None or m.availability.subscription_services:
                kept.append(r)  # unknown stays (labelled in the UI); known-not-streaming drops out
            else:
                dropped += 1
        page.items = kept + rest
        page.total = max(page.total - dropped, len(page.items))
        return page


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
