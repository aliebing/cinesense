from datetime import date

import numpy as np

from cinesense.ingest.movielens import MovieLensFilm
from cinesense.ingest.pipeline import FILM_COLUMNS, film_row, people_rows
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
        title_de="Interstellar (Film)",
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
    assert row["title_de"] == "Interstellar (Film)" and "title_de" in FILM_COLUMNS


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

    async def no_tie(qids, client):
        return {}

    monkeypatch.setattr(pipeline, "fetch_wikidata", fake_fetch)
    monkeypatch.setattr(pipeline, "fetch_languages", no_tie)
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


def test_link_wikidata_fills_german_title_article_and_trailer_of_live_imports(monkeypatch):
    import asyncio

    from cinesense.ingest import pipeline
    from cinesense.ingest.wikidata import WikidataFilm

    async def fake_fetch(imdb_ids, client):
        assert imdb_ids == ["tt0057687"]
        return {
            "tt0057687": WikidataFilm(
                movielens_id=None, wikidata_id="Q571904", imdb_id="tt0057687", title_de="Winnetou 1. Teil",
                wikipedia_title="Apache Gold", youtube_key="abc123", original_language="de",
            )
        }  # fmt: skip

    async def no_tie(qids, client):
        return {}

    monkeypatch.setattr(pipeline, "fetch_by_imdb", fake_fetch)
    monkeypatch.setattr(pipeline, "fetch_languages", no_tie)
    executed = []

    class Conn:
        def execute(self, sql, params=()):
            executed.append((sql, params))

            class R:
                def fetchall(self):
                    return [("imdb-tt0057687", "tt0057687")]

            return R()

        def commit(self):
            executed.append(("commit", ()))

    linked = asyncio.run(pipeline.link_wikidata(Conn(), ["imdb-tt0057687"]))
    assert linked == 1
    update = next(p for sql, p in executed if sql.startswith("update films"))
    assert {"Q571904", "Winnetou 1. Teil", "Apache Gold", "abc123", "de", "imdb-tt0057687"} <= set(update)
    assert executed[-1][0] == "commit"


def test_backfill_german_titles_fills_only_missing_ones(monkeypatch):
    import asyncio

    from cinesense.ingest import pipeline

    async def fake(qids, client):
        assert qids == ["Q1", "Q2"]
        return {"Q1": "Der Schuh des Manitu"}  # Q2 has no German label

    monkeypatch.setattr(pipeline, "fetch_german_titles", fake)
    executed = []

    class Conn:
        def execute(self, sql, params=()):
            class R:
                def fetchall(self):
                    return [("ml-173627", "Q1"), ("ml-2", "Q2")]

            return R()

        def cursor(self):
            class C:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def executemany(self, sql, rows):
                    executed.append((sql, rows))

            return C()

        def commit(self):
            pass

    assert asyncio.run(pipeline.backfill_german_titles(Conn())) == 1
    sql, rows = executed[0]
    assert "title_de is null" in sql and rows == [("Der Schuh des Manitu", "ml-173627")]


def test_backfill_languages_corrects_only_changed_films(monkeypatch):
    import asyncio

    from cinesense.ingest import pipeline

    async def fake(qids, client):
        assert qids == ["Q19355", "Q2", "Q3"]
        return {"Q19355": "it", "Q2": "en"}  # Q3: Wikidata names no language, the old one stays

    monkeypatch.setattr(pipeline, "fetch_languages", fake)
    executed = []

    class Conn:
        def execute(self, sql, params=()):
            class R:
                def fetchall(self):
                    return [("ml-2324", "Q19355", "de"), ("ml-2", "Q2", "en"), ("ml-3", "Q3", "fr")]

            return R()

        def cursor(self):
            class C:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def executemany(self, sql, rows):
                    executed.append((sql, rows))

            return C()

        def commit(self):
            pass

    assert asyncio.run(pipeline.backfill_languages(Conn())) == [("ml-2324", "de", "it")]
    assert executed == [("update films set original_language = %s where id = %s", [("it", "ml-2324")])]
