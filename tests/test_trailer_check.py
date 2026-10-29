import httpx
import respx

from cinesense.domain.models import Movie
from cinesense.providers.trailer_check import OEMBED_URL, TrailerChecker
from cinesense.providers.youtube import MemoryTrailerStore


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
