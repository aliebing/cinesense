import httpx
import respx

from cinesense.ingest.wikipedia import API_URL, chunk_text, extract_plot, fetch_plot

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
