"""Snapshot a small real-data fixture from the Supabase catalogue (offline tests and demos).

    uv run python scripts/make_real_fixtures.py

Per world: the 8 most-rated films with a trailer plus 1 without (Review Focus), with sparse Tag Genome vectors
(top 50), people and — for at most 20 films — cached Streaming Availability payloads (≤ 20 API requests).
"""

import json
from pathlib import Path

import numpy as np

from cinesense.config import get_settings, load_env_file
from cinesense.db import connect
from cinesense.domain.worlds import WORLDS
from cinesense.providers.postgres import PostgresProvider
from cinesense.providers.streaming import PostgresStreamingStore, StreamingClient

OUT = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "movies.json"
MAX_STREAMING = 20


def main() -> None:
    load_env_file()
    s = get_settings()
    cf = lambda: connect(s.database_url)  # noqa: E731
    provider = PostgresProvider(cf)
    streaming = (
        StreamingClient(s.streaming_api_key, PostgresStreamingStore(cf)) if s.streaming_api_key else None
    )
    movies = provider.list_movies()
    picked: dict[str, object] = {}
    for w in WORLDS:
        in_world = sorted(
            (m for m in movies if w.id in m.world_ids), key=lambda m: m.ml_rating_count, reverse=True
        )
        with_trailer = [m for m in in_world if m.youtube_key and m.id not in picked][:8]
        without = [m for m in in_world if not m.youtube_key and m.id not in picked][:1]
        for m in with_trailer + without:
            picked[m.id] = m
    ids = list(picked)
    vectors = provider.tag_vectors(ids)
    with cf() as c:
        people = c.execute(
            "select film_id, name, role from film_people where film_id = any(%s) order by role, ord", (ids,)
        ).fetchall()
    by_film: dict[str, list] = {}
    for film_id, name, role in people:
        by_film.setdefault(film_id, []).append({"name": name, "role": role})
    used = 0
    out = []
    for row, film_id in enumerate(ids):
        m = picked[film_id]
        if streaming and used < MAX_STREAMING and m.imdb_id:
            m.availability.streaming_de = streaming.get_de(m.imdb_id)
            images = streaming.images(m.imdb_id)
            if images:
                m.poster_url, m.horizontal_poster_url, m.backdrop_url = (
                    images.vertical_poster,
                    images.horizontal_poster,
                    images.horizontal_backdrop,
                )
            used += 1
        d = json.loads(m.model_dump_json())
        d["availability"].pop("subscription_services", None)
        v = vectors[row]
        if not np.isnan(v).any():
            top = np.argsort(-v)[:50]
            d["tag_vector_sparse"] = {str(int(i)): round(float(v[i]), 4) for i in top}
        d["people"] = by_film.get(film_id, [])[:30]
        out.append(d)
    OUT.write_text(
        json.dumps({"tags": provider.list_tags(), "movies": out}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(out)} films to {OUT} ({used} streaming lookups)")


if __name__ == "__main__":
    main()
