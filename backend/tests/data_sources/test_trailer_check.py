import httpx
import respx

from cinesense.core.models import Movie
from cinesense.data_sources.trailer_check import OEMBED_URL, TrailerChecker
from cinesense.data_sources.youtube import MemoryTrailerStore


def film(i, key):
    return Movie(id=f"m{i}", title=f"F{i}", youtube_key=key)


@respx.mock
def test_dead_or_unembeddable_trailers_are_dropped_and_cached():
    route = respx.get(OEMBED_URL).mock(side_effect=lambda req: httpx.Response(200 if "good" in str(req.url) else 401))
    checker = TrailerChecker(MemoryTrailerStore(), httpx.Client())
    movies = [film(1, "good1"), film(2, "bad2"), film(3, None)]
    checker.filter_playable(movies)
    assert [m.youtube_key for m in movies] == ["good1", None, None]
    calls = route.call_count
    checker.filter_playable([film(4, "good1"), film(5, "bad2")])
    assert route.call_count == calls  # cached


@respx.mock
def test_network_error_keeps_the_trailer():
    respx.get(OEMBED_URL).mock(side_effect=httpx.ConnectError("offline"))
    movies = [film(1, "abc123")]
    TrailerChecker(MemoryTrailerStore(), httpx.Client()).filter_playable(movies)
    assert movies[0].youtube_key == "abc123"


@respx.mock
def test_player_report_marks_a_trailer_bad_even_if_oembed_says_ok():
    respx.get(OEMBED_URL).mock(return_value=httpx.Response(200))
    store = MemoryTrailerStore()
    checker = TrailerChecker(store, httpx.Client())
    checker.mark_bad("blockedDE")
    movies = [film(1, "blockedDE")]
    TrailerChecker(store, httpx.Client()).filter_playable(movies)  # a new process still knows it
    assert movies[0].youtube_key is None


@respx.mock
def test_unknown_verdicts_are_cached_briefly_and_never_block():
    route = respx.get(OEMBED_URL).mock(return_value=httpx.Response(429))
    checker = TrailerChecker(MemoryTrailerStore(), httpx.Client())
    movies = [film(1, "rateLimited1")]
    checker.filter_playable(movies)
    checker.filter_playable([film(2, "rateLimited1")])
    assert movies[0].youtube_key == "rateLimited1" and route.call_count == 1


def test_known_verdicts_come_from_the_store_in_one_batch():
    class CountingStore(MemoryTrailerStore):
        batches = 0

        def get_many(self, keys):
            CountingStore.batches += 1
            return {k: self.get(k) for k in keys if self.get(k) is not None}

    store = CountingStore()
    store.put("check:deadOne1", None)
    checker = TrailerChecker(store, httpx.Client())
    movies = [film(1, "deadOne1")]
    checker.filter_known(movies)  # never calls YouTube
    assert movies[0].youtube_key is None and CountingStore.batches == 1


def test_report_accepts_only_known_ids_and_is_rate_limited():
    checker = TrailerChecker(MemoryTrailerStore(), httpx.Client())
    assert not checker.report("neverServed1", "user-1234-abcd", known=False)
    assert checker.report("servedKey01", "user-1234-abcd", known=True)
    accepted = [checker.report(f"k{i:09d}", "user-1234-abcd", known=True) for i in range(40)]
    assert accepted.count(False) > 0  # per-user limit


def status(vid, embeddable=True, privacy="public", region=None, rating=None):
    details = {"contentRating": {"ytRating": rating} if rating else {}}
    if region:
        details["regionRestriction"] = region
    return {"id": vid, "status": {"embeddable": embeddable, "privacyStatus": privacy}, "contentDetails": details}


@respx.mock
def test_with_an_api_key_the_video_status_decides_in_one_batch():
    from cinesense.data_sources.trailer_check import VIDEOS_URL

    items = [
        status("ok1"),
        status("noembed", embeddable=False),
        status("blockedDE", region={"blocked": ["AT", "DE"]}),
        status("onlyUS", region={"allowed": ["US"]}),
        status("adult", rating="ytAgeRestricted"),
        status("private", privacy="private"),
    ]  # "deleted" is missing from the answer
    videos = respx.get(VIDEOS_URL).mock(return_value=httpx.Response(200, json={"items": items}))
    oembed = respx.get(OEMBED_URL).mock(return_value=httpx.Response(200))
    keys = ["ok1", "noembed", "blockedDE", "onlyUS", "adult", "private", "deleted"]
    movies = [film(i, k) for i, k in enumerate(keys)]
    TrailerChecker(MemoryTrailerStore(), httpx.Client(), api_key="k").filter_playable(movies)
    assert [m.youtube_key for m in movies] == ["ok1"] + [None] * 6
    assert videos.call_count == 1  # one request for all (1 quota unit for up to 50 videos)
    assert oembed.call_count == 0


@respx.mock
def test_api_failure_falls_back_to_oembed():
    from cinesense.data_sources.trailer_check import VIDEOS_URL

    respx.get(VIDEOS_URL).mock(return_value=httpx.Response(403))
    respx.get(OEMBED_URL).mock(return_value=httpx.Response(200))
    movies = [film(1, "abc123")]
    TrailerChecker(MemoryTrailerStore(), httpx.Client(), api_key="k").filter_playable(movies)
    assert movies[0].youtube_key == "abc123"


@respx.mock
def test_without_api_budget_oembed_is_used():
    from cinesense.data_sources.trailer_check import VIDEOS_URL

    videos = respx.get(VIDEOS_URL).mock(return_value=httpx.Response(200, json={"items": []}))
    respx.get(OEMBED_URL).mock(return_value=httpx.Response(200))
    movies = [film(1, "abc123")]
    TrailerChecker(MemoryTrailerStore(), httpx.Client(), api_key="k", daily_api_calls=0).filter_playable(movies)
    assert videos.call_count == 0
    assert movies[0].youtube_key == "abc123"
