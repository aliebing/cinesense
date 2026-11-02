from cinesense.domain.criteria import SearchCriteria
from cinesense.providers.fixture import FixtureProvider
from cinesense.search.service import SearchService


class CountingStreaming:
    def __init__(self):
        self.calls = 0

    def get_de(self, imdb_id):
        self.calls += 1
        return None


class ExplodingLive:
    def search_title(self, q):
        raise AssertionError("live search during count")

    def search_person(self, q):
        raise AssertionError("live search during count")


class CountingEmbedder:
    def __init__(self):
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        return [[0.0] * 4 for _ in texts]


def test_count_matches_run_total():
    s = SearchService(FixtureProvider())
    c = SearchCriteria(max_runtime_min=100)
    assert s.count(c) == s.run(c, 0, 100).total


def test_count_makes_no_streaming_or_live_calls():
    st = CountingStreaming()
    s = SearchService(FixtureProvider(), streaming=st, live=ExplodingLive())
    s.count(SearchCriteria(availability="stream", title="Zzzz"))
    assert st.calls == 0


def test_embedding_is_cached_per_text():
    e = CountingEmbedder()
    s = SearchService(FixtureProvider(), embedder=e)
    s.count(SearchCriteria(plot_query="heist"))
    s.run(SearchCriteria(plot_query="heist"), 0, 5)
    assert e.calls == 1


def test_can_embed():
    assert SearchService(FixtureProvider()).can_embed("x") is False
    assert SearchService(FixtureProvider(), embedder=CountingEmbedder()).can_embed("x") is True


def test_cinema_plot_search_ranks_only_cinema_films():
    class Recording(FixtureProvider):
        def __init__(self):
            super().__init__()
            self._by_id["ml-1265"].availability.in_cinema_de = True
            self.only = "unset"

        def semantic_search(self, query_embedding, k=20, only_ids=None):
            self.only = only_ids
            return [(self._by_id["ml-1265"], 0.4, "chunk")] if only_ids else []

    p = Recording()
    s = SearchService(p, embedder=CountingEmbedder())
    assert s.count(SearchCriteria(plot_query="funny", availability="cinema")) == 1
    assert p.only == ["ml-1265"]
    s.count(SearchCriteria(plot_query="funny"))
    assert p.only is None
