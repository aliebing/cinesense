import numpy as np
import pytest

from cinesense.core.worlds_map import assign_worlds, normalise_wikidata_genres, top_tags, world_scores


@pytest.mark.parametrize(
    ("genres", "expected"),
    [
        (["Thriller"], ["suspense"]),
        (["Film-Noir", "Crime"], ["suspense"]),
        (["Sci-Fi", "Action"], ["scifi", "action"]),
        (["Romance"], ["romance"]),
        (["Adventure", "Fantasy"], ["adventure"]),
        (["Children", "Animation"], ["comedy"]),
        (["Documentary"], []),
        (["Drama"], ["drama"]),  # every feature film has a world now
        (["Horror"], ["suspense"]),
        (["War", "Drama"], ["drama"]),  # Drama & Life: Schindler's List, 1917
        (["Drama", "Horror", "Thriller"], ["suspense"]),  # the fallbacks only when nothing else places it
        (["Western"], ["adventure"]),
        (["Musical"], ["romance"]),
    ],
)
def test_assign_worlds_mapping(genres, expected):
    assert assign_worlds(genres, []) == expected


def test_drama_with_romantic_tag_is_romance():
    assert assign_worlds(["Drama"], ["romantic", "dark"]) == ["romance"]


def test_top_tags_returns_highest_relevance():
    v = np.zeros(4, dtype=np.float32)
    v[2], v[0] = 0.9, 0.5
    assert top_tags(v, ["a", "b", "c", "d"], k=2) == ["c", "a"]
    assert top_tags(None, ["a"], k=2) == []


def test_normalise_wikidata_genres():
    assert normalise_wikidata_genres(
        ["science fiction film", "action film", "romantic comedy", "documentary film"]
    ) == [
        "Sci-Fi",
        "Action",
        "Romance",
        "Comedy",
        "Documentary",
    ]


def test_the_main_world_comes_first_by_the_films_mood_tags():
    tags = ["sci-fi", "crime", "action", "suspense"]
    v = np.array([1.0, 0.4, 0.6, 0.5], dtype=np.float32)  # Inception: strongly sci-fi
    genres = ["Action", "Crime", "Mystery", "Sci-Fi", "Thriller"]
    assert assign_worlds(genres, [], world_scores(v, tags)) == ["scifi", "action", "suspense"]
    assert assign_worlds(genres, []) == ["suspense", "scifi", "action"]  # without mood data: the fixed order
