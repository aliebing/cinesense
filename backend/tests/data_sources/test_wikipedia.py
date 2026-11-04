import httpx
import respx

from cinesense.data_sources.wikipedia import API_URL, chunk_text, extract_plot, fetch_plot

EXTRACT = (
    "Intro line.\n\n== Plot ==\nIn the near future, crops fail.\n\n=== Act one ===\n"
    "Cooper joins a mission.\n\n== Cast ==\nMatthew McConaughey\n"
)


def test_extract_plot_section_only():
    assert extract_plot(EXTRACT) == "In the near future, crops fail.\n\nCooper joins a mission."


def test_extract_plot_accepts_synopsis_and_none_without_section():
    assert extract_plot("== Synopsis ==\nA story.\n\n== Reception ==\nGood.") == "A story."
    assert extract_plot("Intro only.\n\n== Reception ==\nGood.") is None


@respx.mock
async def test_fetch_plot_none_for_disambiguation_and_missing():
    respx.get(API_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "query": {"pages": {"1": {"title": "X", "pageprops": {"disambiguation": ""}, "extract": EXTRACT}}}
                },
            ),
            httpx.Response(200, json={"query": {"pages": {"-1": {"title": "Y", "missing": ""}}}}),
            httpx.Response(200, json={"query": {"pages": {"2": {"title": "Z", "extract": EXTRACT}}}}),
        ]
    )
    async with httpx.AsyncClient() as c:
        assert await fetch_plot("X", c) is None
        assert await fetch_plot("Y", c) is None
        assert (await fetch_plot("Z", c)).startswith("In the near future")


def test_chunk_text_respects_limits_and_overlap():
    para = " ".join(f"Sentence number {i} tells part of the story." for i in range(60))
    chunks = chunk_text(para, max_chars=300, overlap=60)
    assert len(chunks) > 3
    assert all(len(c) <= 300 for c in chunks)
    for a, b in zip(chunks, chunks[1:], strict=False):
        assert set(a.split()[-5:]) & set(b.split()[:15])  # overlap shares words
    assert "Sentence number 59" in chunks[-1]


def test_chunk_text_short_text_single_chunk():
    assert chunk_text("Short plot.") == ["Short plot."]


@respx.mock
async def test_fetch_plot_raises_when_rate_limited_throughout(monkeypatch):
    import asyncio

    import pytest

    async def no_sleep(_):
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    respx.get(API_URL).mock(return_value=httpx.Response(429))
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError):  # "retry next run", never "this film has no plot"
            await fetch_plot("Alien (film)", client)


def test_posters_from_page_images_follow_redirects_and_keep_only_portrait_images():
    from cinesense.data_sources.wikipedia import posters_from_query

    data = {
        "query": {
            "normalized": [{"from": "two If by Sea", "to": "Two If by Sea"}],
            "redirects": [{"from": "Love Potion 9", "to": "Love Potion No. 9 (film)"}],
            "pages": [
                {
                    "title": "Two If by Sea",
                    "thumbnail": {
                        "source": "https://upload.wikimedia.org/a.jpg?utm_source=x",
                        "width": 258,
                        "height": 386,
                    },
                },
                {
                    "title": "Love Potion No. 9 (film)",
                    "thumbnail": {"source": "https://upload.wikimedia.org/b.jpg", "width": 248, "height": 370},
                },
                {
                    "title": "Some Film",
                    "thumbnail": {"source": "https://upload.wikimedia.org/scene.jpg", "width": 400, "height": 225},
                },
                {"title": "No Image Film"},
                {"title": "Gone", "missing": True},
            ],
        }
    }
    asked = ["two If by Sea", "Love Potion 9", "Some Film", "No Image Film", "Gone"]
    assert posters_from_query(data, asked) == {
        "two If by Sea": "https://upload.wikimedia.org/a.jpg",  # tracking parameters dropped
        "Love Potion 9": "https://upload.wikimedia.org/b.jpg",
    }
