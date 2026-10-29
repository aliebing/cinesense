"""Run a SearchCriteria against the catalogue: candidate generation per signal, then combined ranking."""

import asyncio
import logging

from cinesense.domain.criteria import MUST_THRESHOLD, NOT_THRESHOLD, SearchCriteria
from cinesense.recommend.combined import CombinedResult, Signals, combined_rank

log = logging.getLogger(__name__)
STREAM_CHECK_LIMIT = 30  # streaming lookups per search (free plan budget)


class SearchService:
    def __init__(self, provider, streaming=None, embedder=None) -> None:
        self.provider = provider
        self.streaming = streaming
        self.embedder = embedder

    def _embed(self, text: str) -> list[float] | None:
        if self.embedder is None:
            return None
        try:
            return asyncio.run(self.embedder.embed([text]))[0]
        except Exception as exc:  # noqa: BLE001 — degrade to no plot signal
            log.warning("embedding failed: %s", exc)
            return None

    def run(self, c: SearchCriteria, offset: int = 0, limit: int = 20) -> CombinedResult:
        p = self.provider
        sig = Signals(tag_names=dict(enumerate(p.list_tags())) if c.has_tags() else {})
        restrict: set[str] | None = None
        hidden = 0

        if c.has_tags():
            hits, hidden = p.tag_search(
                c.prefer_weights(), c.must_tags(), c.not_tags(), MUST_THRESHOLD, NOT_THRESHOLD
            )
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

        movies = p.list_movies()
        if restrict is not None:
            movies = [m for m in movies if m.id in restrict]
        result = combined_rank(movies, c, sig, hidden_by_tags=hidden, offset=0, limit=len(movies) or 1)

        if c.has_tags():
            top_ids = [r.movie.id for r in result.items[: offset + limit]]
            vectors = p.tag_vectors(top_ids)
            idxs = [t.idx for t in c.tags]
            sig.tag_relevance = {
                fid: {i: float(vectors[row][i]) for i in idxs} for row, fid in enumerate(top_ids)
            }
        page = combined_rank(
            [r.movie for r in result.items], c, sig, hidden_by_tags=0, offset=offset, limit=limit
        )
        page.hidden_by_exclusion = result.hidden_by_exclusion
        if c.availability == "stream":
            page = self._resolve_streaming(page)
        return page

    def _resolve_streaming(self, page: CombinedResult) -> CombinedResult:
        if self.streaming is None:
            return page
        kept = []
        for r in page.items[:STREAM_CHECK_LIMIT]:
            m = r.movie
            if m.imdb_id and m.availability.streaming_de is None:
                m.availability.streaming_de = self.streaming.get_de(m.imdb_id)
            if m.availability.streaming_de is None or m.availability.subscription_services:
                kept.append(r)  # unknown stays (labelled in the UI); known-not-streaming drops out
        page.items = kept + page.items[STREAM_CHECK_LIMIT:]
        return page
