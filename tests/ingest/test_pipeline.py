from datetime import date

import numpy as np

from cinesense.ingest.movielens import MovieLensFilm
from cinesense.ingest.pipeline import film_row, people_rows
from cinesense.ingest.wikidata import WikidataFilm


def test_film_row_from_sources():
    vec = np.zeros(1128, dtype=np.float32)
    vec[5] = 0.95
    ml = MovieLensFilm(109487, "Interstellar", 2014, ["Sci-Fi", "IMAX"], 4.1, 30000, vec)
    wd = WikidataFilm(
        109487,
        "Q13417189",
        imdb_id="tt0816692",
        youtube_key="F6TU69adAzE",
        runtime_min=169,
        original_language="en",
        release_date_de=date(2014, 11, 6),
        wikipedia_title="Interstellar (film)",
        directors=["Christopher Nolan"],
        cast=[f"Actor {i}" for i in range(8)],
    )
    tags = [f"tag{i}" for i in range(1128)]
    row = film_row(ml, wd, tags)
    assert row["id"] == "ml-109487" and row["kind"] == "film"
    assert row["world_ids"] == ["scifi"] and row["top_tags"][0] == "tag5"
    assert row["cast_top"] == [f"Actor {i}" for i in range(5)]
    assert row["imdb_id"] == "tt0816692" and row["release_date_de"] == date(2014, 11, 6)
    assert row["tag_vector"].shape == (1128,)


def test_people_rows_cast_and_directors():
    wd = WikidataFilm(1, "Q1", directors=["D One"], cast=["A", "B"])
    assert people_rows("ml-1", wd) == [
        ("ml-1", "D One", "director", 0),
        ("ml-1", "A", "cast", 0),
        ("ml-1", "B", "cast", 1),
    ]


def test_documentary_without_vector_kind():
    ml = MovieLensFilm(5, "Some Doc", 2005, ["Documentary"], 3.9, 40, None)
    row = film_row(ml, WikidataFilm(5, "Q5"), [])
    assert row["kind"] == "documentary" and row["tag_vector"] is None and row["top_tags"] == []


def test_duplicate_wikidata_items_keep_first(monkeypatch):
    """Two MovieLens ids mapping to one Wikidata item: only the first (most-rated) is kept."""
    import asyncio

    from cinesense.ingest import pipeline

    vec = np.zeros(1128, dtype=np.float32)
    films = [
        MovieLensFilm(1, "A", 2000, ["Action"], 4.0, 900, vec),
        MovieLensFilm(2, "A (dup)", 2000, ["Action"], 3.0, 10, vec),
    ]
    monkeypatch.setattr(pipeline, "read_genome_tags", lambda p: ["t"] * 1128)
    monkeypatch.setattr(pipeline, "read_films", lambda p: films)
    monkeypatch.setattr(pipeline, "read_documentaries_without_genome", lambda p: [])

    async def fake_fetch(ids, client):
        return {i: WikidataFilm(i, "Q1") for i in ids}

    monkeypatch.setattr(pipeline, "fetch_wikidata", fake_fetch)
    upserted = []
    monkeypatch.setattr(pipeline, "_upsert_films", lambda conn, rows: upserted.extend(rows))
    monkeypatch.setattr(pipeline, "_replace_people", lambda conn, ids, rows: None)

    class Conn:
        def cursor(self):
            class Cur:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def executemany(self, *a):
                    return None

            return Cur()

        def commit(self):
            return None

        def execute(self, *a):
            class R:
                def fetchall(self):
                    return []

            return R()

    asyncio.run(pipeline.ingest_catalogue(Conn(), "x", None, with_extras=False))
    assert [r["id"] for r in upserted] == ["ml-1"]


def test_ingest_plots_limits_to_given_ids():
    import asyncio

    from cinesense.ingest.pipeline import ingest_plots

    seen = {}

    class Conn:
        def execute(self, sql, params=()):
            seen["sql"], seen["params"] = sql, params

            class R:
                def fetchall(self):
                    return []

            return R()

    asyncio.run(ingest_plots(Conn(), None, None, ids=["wd-Q1", "imdb-tt2"]))
    assert "id = any(%s)" in seen["sql"]
    assert seen["params"] == (["wd-Q1", "imdb-tt2"],)
