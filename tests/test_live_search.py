import httpx
import respx

from cinesense.ingest.wikidata import SPARQL_URL
from cinesense.providers.live_search import WBSEARCH_URL, LiveSearch
from cinesense.providers.streaming import BASE_URL, MemoryStreamingStore, StreamingClient

SHOW = {
    "imdbId": "tt9999999",
    "title": "Brand New Film",
    "releaseYear": 2025,
    "runtime": 118,
    "genres": [{"id": "scifi", "name": "Science Fiction"}],
    "overview": "A new film.",
    "directors": ["Jane Director"],
    "cast": ["Ann Actor", "Bob Actor"],
    "streamingOptions": {"de": [{"service": {"name": "Netflix"}, "type": "subscription"}]},
    "imageSet": {
        "verticalPoster": {"w480": "v.jpg"},
        "horizontalPoster": {"w720": "h.jpg"},
        "horizontalBackdrop": {"w1080": "b.jpg"},
    },
}


def streaming():
    return StreamingClient("k", MemoryStreamingStore(), http=httpx.Client())


@respx.mock
def test_live_title_search_maps_streaming_and_images():
    route = respx.get(f"{BASE_URL}/shows/search/title").mock(return_value=httpx.Response(200, json=[SHOW]))
    hits = LiveSearch(streaming(), http=httpx.Client()).search_title("brand new flim")
    assert route.call_count == 1
    m = hits[0]
    assert m.id == "imdb-tt9999999" and m.title == "Brand New Film" and m.year == 2025
    assert m.availability.subscription_services == ["Netflix"]
    assert m.horizontal_poster_url == "h.jpg" and m.genres == ["Sci-Fi"] and "scifi" in m.world_ids


@respx.mock
def test_live_person_search_newest_first():
    respx.get(WBSEARCH_URL).mock(
        return_value=httpx.Response(
            200, json={"search": [{"id": "Q123", "label": "Sandra Hüller", "description": "German actress"}]}
        )
    )
    rows = [
        {
            "film": {"value": "http://www.wikidata.org/entity/Q1"},
            "filmLabel": {"value": "Old Film"},
            "pub": {"value": "2009-01-01T00:00:00Z"},
            "role": {"value": "cast"},
        },
        {
            "film": {"value": "http://www.wikidata.org/entity/Q2"},
            "filmLabel": {"value": "New Film"},
            "pub": {"value": "2023-05-01T00:00:00Z"},
            "imdb": {"value": "tt2"},
            "role": {"value": "cast"},
        },
    ]
    respx.post(SPARQL_URL).mock(return_value=httpx.Response(200, json={"results": {"bindings": rows}}))
    name, films = LiveSearch(None, http=httpx.Client()).search_person("Sandra Hueller")
    assert name == "Sandra Hüller"
    assert [f.title for f in films] == ["New Film", "Old Film"]
    assert films[0].id == "wd-Q2" and films[0].imdb_id == "tt2"
