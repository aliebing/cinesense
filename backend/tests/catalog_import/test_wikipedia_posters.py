from cinesense.catalog_import.posters import fill_posters


def test_fills_films_in_batches_and_reports_what_it_found():
    films = [(f"ml-{i}", f"Film {i}") for i in range(120)]
    asked: list[list[str]] = []

    def fetch(titles):
        asked.append(titles)
        return {t: f"https://upload.wikimedia.org/{t}.jpg" for t in titles if not t.endswith("7")}

    saved = {}
    stats = fill_posters(films, fetch, lambda film_id, url: saved.__setitem__(film_id, url), batch=50)
    assert [len(a) for a in asked] == [50, 50, 20]
    assert saved["ml-1"] == "https://upload.wikimedia.org/Film 1.jpg"
    assert "ml-7" not in saved
    assert stats == {"films": 120, "found": len(saved), "requests": 3}


def test_a_failed_batch_is_skipped_not_fatal():
    def fetch(titles):
        if "Film 0" in titles:
            raise RuntimeError("wikipedia down")
        return {t: "u" for t in titles}

    saved = {}
    stats = fill_posters([("a", "Film 0"), ("b", "Film 1")], fetch, lambda f, u: saved.__setitem__(f, u), batch=1)
    assert saved == {"b": "u"}
    assert stats["found"] == 1
