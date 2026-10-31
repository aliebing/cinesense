from datetime import UTC, datetime, timedelta

import httpx
import respx

from cinesense.providers.youtube import SEARCH_URL, MemoryTrailerStore, YouTubeTrailerClient


def item(vid, title):
    return {"id": {"videoId": vid}, "snippet": {"title": title}}


def client(store=None, key="k", limit=95):
    return YouTubeTrailerClient(key, store or MemoryTrailerStore(), daily_limit=limit, http=httpx.Client())


@respx.mock
def test_picks_matching_trailer_title():
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={"items": [item("x1", "Behind the scenes"), item("v2", "AMÉLIE - Official Trailer (2001)")]},
        )
    )
    assert client().find_trailer("ml-1", "Amélie", 2001) == "v2"


@respx.mock
def test_no_match_cached_as_none():
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"items": [item("x1", "Cat video")]}))
    c = client()
    assert c.find_trailer("ml-1", "Amélie", 2001) is None
    assert c.find_trailer("ml-1", "Amélie", 2001) is None
    assert route.call_count == 1


@respx.mock
def test_quota_reached_no_request():
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"items": []}))
    store = MemoryTrailerStore()
    for _ in range(95):
        store.add_call()
    assert client(store).find_trailer("ml-1", "A", None) is None
    assert route.call_count == 0


def test_no_key_returns_none():
    assert client(key=None).find_trailer("ml-1", "A", None) is None


@respx.mock
def test_cache_refreshed_after_30_days():
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"items": [item("v", "A official trailer")]})
    )
    store = MemoryTrailerStore()
    store.put("ml-1", "old", datetime.now(UTC) - timedelta(days=31))
    assert client(store).find_trailer("ml-1", "A", None) == "v"
    assert route.call_count == 1


@respx.mock
def test_key_sent_as_header_and_never_logged(caplog):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(403, json={"error": "quota"}))
    c = YouTubeTrailerClient("SECRET-KEY", MemoryTrailerStore(), http=httpx.Client())
    with caplog.at_level("WARNING"):
        assert c.find_trailer("ml-1", "A", None) is None
    req = route.calls[0].request
    assert req.headers["X-goog-api-key"] == "SECRET-KEY"
    assert "SECRET-KEY" not in str(req.url)
    assert "SECRET-KEY" not in caplog.text


@respx.mock
def test_matches_catalogue_titles_loosely():
    """MovieLens titles carry subtitles, alternate titles and a trailing ", The"; trailers rarely do."""
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"items": [item("sw", "STAR WARS: A NEW HOPE - Official Trailer")]})
    )
    assert client().find_trailer("ml-260", "Star Wars: Episode IV - A New Hope", 1977) == "sw"
    route.mock(return_value=httpx.Response(200, json={"items": [item("rh", "The Road Home (1999) Trailer")]}))
    assert client().find_trailer("ml-1", "Road Home, The (Wo de fu qin mu qin)", 1999) == "rh"
    assert '"The Road Home"' in str(route.calls.last.request.url.params["q"])
    route.mock(return_value=httpx.Response(200, json={"items": [item("x", "Star Trek Official Trailer")]}))
    assert client().find_trailer("ml-2", "Star Wars: Episode IV - A New Hope", 1977) is None
