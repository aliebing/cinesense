"""Curated mapping from genres/tags to the six mood worlds (metadata only — no video understanding)."""

import numpy as np

_WORLD_GENRES = {
    "suspense": {"Mystery", "Thriller", "Crime", "Film-Noir"},
    "scifi": {"Sci-Fi"},
    "romance": {"Romance"},
    "adventure": {"Adventure", "Fantasy"},
    "comedy": {"Comedy", "Children", "Animation"},
    "action": {"Action"},
}
_ORDER = ["suspense", "scifi", "romance", "adventure", "comedy", "action"]
_ROMANTIC_TAGS = {"romantic", "emotional", "romance", "love story"}

# Wikidata genre labels -> MovieLens genre names (substring match, first hit wins per rule)
_WD_GENRE_RULES = [
    ("science fiction", "Sci-Fi"),
    ("action", "Action"),
    ("adventure", "Adventure"),
    ("fantasy", "Fantasy"),
    ("romantic", "Romance"),
    ("romance", "Romance"),
    ("comedy", "Comedy"),
    ("thriller", "Thriller"),
    ("mystery", "Mystery"),
    ("crime", "Crime"),
    ("horror", "Horror"),
    ("drama", "Drama"),
    ("animat", "Animation"),
    ("family", "Children"),
    ("war", "War"),
    ("musical", "Musical"),
    ("western", "Western"),
    ("documentary", "Documentary"),
]


def assign_worlds(genres: list[str], top: list[str]) -> list[str]:
    gs = set(genres)
    worlds = [w for w in _ORDER if gs & _WORLD_GENRES[w]]
    if "romance" not in worlds and "Drama" in gs and _ROMANTIC_TAGS & set(top):
        worlds.insert(_ORDER.index("romance") if not worlds else len(worlds), "romance")
        worlds.sort(key=_ORDER.index)
    return worlds


def top_tags(vector: np.ndarray | None, tags: list[str], k: int = 5) -> list[str]:
    if vector is None or not tags:
        return []
    idx = np.argsort(-vector)[:k]
    return [tags[i] for i in idx]


def normalise_wikidata_genres(labels: list[str]) -> list[str]:
    out: list[str] = []
    for label in labels:
        low = label.lower()
        for needle, genre in _WD_GENRE_RULES:
            if needle in low:
                if genre not in out:
                    out.append(genre)
                if needle in ("romantic",):  # "romantic comedy" is both
                    continue
                if needle != "romantic":
                    break
    return out
