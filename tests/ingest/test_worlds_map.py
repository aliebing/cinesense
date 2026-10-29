import numpy as np
import pytest

from cinesense.ingest.worlds_map import assign_worlds, normalise_wikidata_genres, top_tags


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
        (["Drama"], []),
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
