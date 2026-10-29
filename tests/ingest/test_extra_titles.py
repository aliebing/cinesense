from datetime import date

from cinesense.ingest.extra_titles import fold_recent


def b(**kw):
    return {k: {"value": v} for k, v in kw.items()}


def test_recent_releases_fold_ids_dates_and_genres():
    rows = [
        b(
            film="http://www.wikidata.org/entity/Q1",
            filmLabel="New Film",
            deDate="2024-03-01T00:00:00Z",
            pub="2023-09-01T00:00:00Z",
            imdb="tt1",
            enwiki="https://en.wikipedia.org/wiki/New_Film",
            type="http://www.wikidata.org/entity/Q11424",
        ),
        b(
            film="http://www.wikidata.org/entity/Q1",
            filmLabel="New Film",
            deDate="2024-02-15T00:00:00Z",
            genreLabel="science fiction film",
            type="http://www.wikidata.org/entity/Q11424",
        ),
        b(
            film="http://www.wikidata.org/entity/Q2",
            filmLabel="A Doc",
            deDate="2022-05-05T00:00:00Z",
            enwiki="https://en.wikipedia.org/wiki/A_Doc",
            type="http://www.wikidata.org/entity/Q93204",
        ),
    ]
    out = {r["id"]: r for r in fold_recent(rows)}
    assert out["wd-Q1"]["release_date_de"] == date(2024, 2, 15)
    assert out["wd-Q1"]["year"] == 2023 and out["wd-Q1"]["genres"] == ["Sci-Fi"]
    assert out["wd-Q1"]["kind"] == "film" and out["wd-Q1"]["world_ids"] == ["scifi"]
    assert out["wd-Q2"]["kind"] == "documentary" and out["wd-Q2"]["tag_vector"] is None
