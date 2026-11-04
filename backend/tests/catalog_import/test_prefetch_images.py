from cinesense.catalog_import.images import prefetch


def show(imdb, poster="p.jpg"):
    return {"imdbId": imdb, "imageSet": {"verticalPoster": {"w480": poster}, "horizontalPoster": {"w720": "h.jpg"}}}


def test_walks_pages_and_genres_and_saves_each_film_once():
    pages = {
        ("drama", None): ([show("tt1"), show("tt2")], "c2"),
        ("drama", "c2"): ([show("tt3"), show("tt1")], None),  # tt1 again: saved once
        ("comedy", None): ([show("tt4"), {"imdbId": "tt5"}], None),  # tt5 has no images
    }
    calls, saved = [], []

    def browse(genre, cursor):
        calls.append((genre, cursor))
        return pages[(genre, cursor)]

    stats = prefetch(browse, lambda imdb, *img: saved.append((imdb, img)) or 1, lambda: 99, ["drama", "comedy"])
    assert calls == [("drama", None), ("drama", "c2"), ("comedy", None)]
    assert [s[0] for s in saved] == ["tt1", "tt2", "tt3", "tt4"]
    assert saved[0][1] == ("p.jpg", "h.jpg", None)
    assert stats == {"pages": 3, "shows": 5, "films": 4}


def test_stops_when_the_budget_is_used_up():
    left = [2]

    def browse(genre, cursor):
        left[0] -= 1
        return [show(f"tt-{genre}-{cursor}")], "next"

    stats = prefetch(browse, lambda *a: 1, lambda: left[0], ["drama", "comedy"])
    assert stats["pages"] == 2


def test_a_failed_page_ends_the_genre_not_the_run():
    def browse(genre, cursor):
        return ([], None) if genre == "drama" else ([show("tt9")], None)

    assert prefetch(browse, lambda *a: 1, lambda: 5, ["drama", "comedy"])["films"] == 1
