from datetime import UTC, datetime, timedelta

import httpx
import respx

from cinesense.providers.streaming import BASE_URL, MemoryStreamingStore, StreamingClient

PAYLOAD = {
    "imdbId": "tt0816692",
    "streamingOptions": {
        "de": [
            {"service": {"name": "HBO Max"}, "type": "subscription", "link": "https://hbo.example"},
            {"service": {"name": "Apple TV"}, "type": "rent", "link": None},
        ]
    },
    "imageSet": {
        "verticalPoster": {"w480": "https://cdn/v.jpg"},
        "horizontalPoster": {"w720": "https://cdn/h.jpg"},
        "horizontalBackdrop": {"w1080": "https://cdn/b.jpg"},
    },
}
SHOW = f"{BASE_URL}/shows/tt0816692"


def client(store=None, key="k", limit=900):
    return StreamingClient(key, store or MemoryStreamingStore(), monthly_limit=limit, http=httpx.Client())


@respx.mock
def test_maps_de_options_and_caches():
    route = respx.get(SHOW).mock(return_value=httpx.Response(200, json=PAYLOAD))
    c = client()
    opts = c.get_de("tt0816692")
    assert [(o.service, o.type) for o in opts] == [("HBO Max", "subscription"), ("Apple TV", "rent")]
    c.get_de("tt0816692")
    assert route.call_count == 1
    imgs = c.images("tt0816692")
    assert (imgs.vertical_poster, imgs.horizontal_poster, imgs.horizontal_backdrop) == (
        "https://cdn/v.jpg",
        "https://cdn/h.jpg",
        "https://cdn/b.jpg",
    )


@respx.mock
def test_404_cached_as_empty_list():
    route = respx.get(SHOW).mock(return_value=httpx.Response(404))
    c = client()
    assert c.get_de("tt0816692") == []
    assert c.get_de("tt0816692") == []
    assert route.call_count == 1


@respx.mock
def test_budget_reached_returns_none_without_request():
    route = respx.get(SHOW).mock(return_value=httpx.Response(200, json=PAYLOAD))
    store = MemoryStreamingStore()
    for _ in range(900):
        store.add_call()
    assert client(store).get_de("tt0816692") is None
    assert route.call_count == 0


@respx.mock
def test_http_error_and_timeout_return_none():
    respx.get(SHOW).mock(side_effect=[httpx.Response(500), httpx.ReadTimeout("slow")])
    c = client()
    assert c.get_de("tt0816692") is None
    assert c.get_de("tt0816692") is None


def test_no_api_key_returns_none():
    assert client(key=None).get_de("tt0816692") is None


@respx.mock
def test_cache_older_than_7_days_refetches():
    route = respx.get(SHOW).mock(return_value=httpx.Response(200, json=PAYLOAD))
    store = MemoryStreamingStore()
    store.put("tt0816692", PAYLOAD, fetched_at=datetime.now(UTC) - timedelta(days=8))
    client(store).get_de("tt0816692")
    assert route.call_count == 1


@respx.mock
def test_browse_returns_shows_and_caches_a_day():
    route = respx.get(f"{BASE_URL}/shows/search/filters").mock(
        return_value=httpx.Response(200, json={"shows": [PAYLOAD], "hasMore": True, "nextCursor": "c2"})
    )
    c = client()
    shows, cursor = c.browse("scifi")
    assert len(shows) == 1 and cursor == "c2"
    c.browse("scifi")
    assert route.call_count == 1
