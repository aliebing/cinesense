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
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"items": [item("x1", "Cat video")]})
    )
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
