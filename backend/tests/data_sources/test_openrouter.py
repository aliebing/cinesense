import httpx
import respx

from cinesense.data_sources.openrouter import MODELS_URL, PriceList


@respx.mock
def test_prices_per_token_cached_and_empty_when_unreachable():
    route = respx.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"id": "a/b", "pricing": {"prompt": "0.000001", "completion": "0.000002"}},
                    {"id": "broken", "pricing": {}},
                ]
            },
        )
    )
    now = [0.0]
    pl = PriceList(clock=lambda: now[0])
    assert pl.prices() == {"a/b": (1e-6, 2e-6)}
    pl.prices()
    assert route.call_count == 1  # cached
    route.mock(return_value=httpx.Response(500))
    now[0] = 7 * 3600
    assert pl.prices() == {"a/b": (1e-6, 2e-6)}  # keeps the last good list


@respx.mock
def test_no_list_yet_and_unreachable_gives_empty():
    respx.get(MODELS_URL).mock(side_effect=httpx.ConnectError("down"))
    assert PriceList().prices() == {}
