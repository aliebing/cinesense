import httpx
import respx

from cinesense.catalog_import.billing import fetch_leads
from cinesense.data_sources.wikipedia import API_URL


@respx.mock
async def test_fetch_leads_maps_redirects_back_to_the_asked_titles():
    respx.get(API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "query": {
                    "normalized": [{"from": "life of Pi (film)", "to": "Life of Pi (film)"}],
                    "redirects": [{"from": "Hamlet 1996", "to": "Hamlet (1996 film)"}],
                    "pages": {
                        "1": {"title": "Life of Pi (film)", "extract": "The film stars Suraj Sharma."},
                        "2": {"title": "Hamlet (1996 film)", "extract": "Hamlet stars Kenneth Branagh."},
                        "-1": {"title": "Nope", "missing": ""},
                    },
                }
            },
        )
    )
    async with httpx.AsyncClient() as c:
        leads = await fetch_leads(["life of Pi (film)", "Hamlet 1996", "Nope"], c)
    assert leads == {
        "life of Pi (film)": "The film stars Suraj Sharma.",
        "Hamlet 1996": "Hamlet stars Kenneth Branagh.",
    }
