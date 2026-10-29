import json

import httpx
import respx

from cinesense.ingest.embeddings import EMBEDDINGS_URL, EmbeddingClient


@respx.mock
async def test_embed_batches_and_preserves_order():
    def reply(request):
        inputs = json.loads(request.content)["input"]
        data = [{"index": i, "embedding": [float(len(t))] + [0.0] * 1535} for i, t in enumerate(inputs)]
        return httpx.Response(
            200, json={"data": list(reversed(data)), "usage": {"total_tokens": 5, "cost": 0.0001}}
        )

    route = respx.post(EMBEDDINGS_URL).mock(side_effect=reply)
    texts = ["x" * (i % 7 + 1) for i in range(230)]
    async with httpx.AsyncClient() as http:
        client = EmbeddingClient("key", http=http)
        vectors = await client.embed(texts)
    assert route.call_count == 3
    assert len(vectors) == 230 and all(len(v) == 1536 for v in vectors)
    assert [v[0] for v in vectors] == [float(len(t)) for t in texts]
    assert client.total_tokens == 15
