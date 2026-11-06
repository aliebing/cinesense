import threading
from contextlib import contextmanager
from datetime import date

from cinesense.data_sources.postgres import _NAMES, PostgresProvider


def row(i):
    d = {n: None for n in _NAMES}
    d.update(
        id=f"ml-{i}",
        title=f"F{i}",
        kind="film",
        genres=[],
        world_ids=["action"],
        top_tags=[],
        overview="",
        directors=[],
        cast_top=[],
        ml_rating_count=10,
        release_date_de=date(2000, 1, 1),
        images_checked=False,
    )
    return tuple(d[n] for n in _NAMES)


class FakeConn:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, params=None):
        self.log.append(sql)

        class R:
            def fetchall(_):
                return [row(i) for i in range(50)]

            def fetchone(_):
                return None

        return R()

    def commit(self):
        pass


def provider(log):
    @contextmanager
    def cf():
        yield FakeConn(log)

    return PostgresProvider(cf)


def test_list_movies_survives_concurrent_image_updates():
    p = provider([])
    errors = []

    def reader():
        try:
            for _ in range(200):
                assert len(p.list_movies()) == 50
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def writer():
        for i in range(200):
            p.update_images(f"ml-{i % 50}", "v", "h", "b")

    threads = [threading.Thread(target=reader) for _ in range(4)] + [threading.Thread(target=writer)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors


def test_image_update_patches_cache_without_reloading():
    log = []
    p = provider(log)
    p.list_movies()
    loads = sum(1 for s in log if s.startswith("select") and "from films" in s and "where" not in s)
    p.update_images("ml-3", "v.jpg", "h.jpg", "b.jpg")
    m = next(m for m in p.list_movies() if m.id == "ml-3")
    assert m.horizontal_poster_url == "h.jpg" and m.images_checked
    assert sum(1 for s in log if s.startswith("select") and "from films" in s and "where" not in s) == loads


def test_list_movies_shares_cached_objects_and_search_results_are_copies():
    from cinesense.core.criteria import SearchCriteria
    from cinesense.search.service import SearchService

    p = provider([])
    a, b = p.list_movies(), p.list_movies()
    assert a[0] is b[0]  # no per-call deep copy of ~20k films
    page = SearchService(p).run(SearchCriteria(), 0, 5)
    page.items[0].movie.title = "mutated"
    assert all(m.title != "mutated" for m in p.list_movies())


def test_stale_catalogue_is_served_while_it_reloads_in_the_background():
    log = []
    p = provider(log)
    first = p.list_movies()
    assert len(log) == 1  # the very first call waits for the load
    gate = threading.Event()
    reloaded = threading.Event()
    original = p._reload

    def slow_reload():
        gate.wait(5)
        out = original()
        reloaded.set()
        return out

    p._reload = slow_reload
    p._loaded_at -= p._cache_seconds + 1  # stale
    again = p.list_movies()  # answers at once with the old films, the reload runs on
    assert [m.id for m in again] == [m.id for m in first] and not reloaded.is_set()
    p.list_movies()  # a second call meanwhile starts no second reload
    gate.set()
    assert reloaded.wait(5)
    assert len(log) == 2
