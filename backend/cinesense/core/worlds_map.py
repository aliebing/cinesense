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
# a film none of those genres places (a pure drama, a horror or war film, a western, a musical) still gets a world,
# so every feature film belongs somewhere; documentaries alone stay outside (the search has a filter for them).
# Only as a fallback: Inception or The Shining are not love stories because they are also dramas
_FALLBACK_GENRES = {
    "suspense": {"Horror"},
    "romance": {"Musical"},
    "adventure": {"Western"},
    "action": {"War"},
}
_LAST_RESORT = {"Drama": "romance"}  # a drama with nothing else to go by (a war drama is a war film first)
# the Tag Genome tags that say how strongly a film is of each world: its main world (listed first) is the strongest
# (Inception: Action, Crime, Mystery, Sci-Fi, Thriller; "sci-fi" 100% makes it Science Fiction, not Suspense)
_WORLD_TAGS = {
    "suspense": ("suspense", "mystery", "thriller", "crime", "horror"),
    "scifi": ("sci-fi", "science fiction", "space", "future"),
    "romance": ("romance", "romantic", "love story", "emotional", "drama"),
    "adventure": ("adventure", "fantasy", "western"),
    "comedy": ("comedy", "funny", "humorous"),
    "action": ("action", "action packed", "war"),
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


def world_scores(vector: np.ndarray | None, tags: list[str]) -> dict[str, float]:
    """How strongly a film is of each world: the highest relevance among the world's tags (0 without data)."""
    if vector is None or not tags:
        return {}
    idx = {t: i for i, t in enumerate(tags)}
    out = {}
    for w, names in _WORLD_TAGS.items():
        values = [float(vector[idx[n]]) for n in names if n in idx and idx[n] < len(vector)]
        values = [v for v in values if v == v]  # NaN: no Tag Genome data
        out[w] = max(values, default=0.0)
    return out


def assign_worlds(genres: list[str], top: list[str], scores: dict[str, float] | None = None) -> list[str]:
    """The worlds of a film from its genres, its main world first: the one its mood tags show most strongly
    (`scores`), else the fixed world order."""
    gs = set(genres)
    worlds = [w for w in _ORDER if gs & _WORLD_GENRES[w]]
    if "romance" not in worlds and "Drama" in gs and _ROMANTIC_TAGS & set(top):
        worlds.append("romance")
        worlds.sort(key=_ORDER.index)
    if not worlds:
        worlds = [w for w in _ORDER if gs & _FALLBACK_GENRES.get(w, set())]
    if not worlds:
        worlds = [w for g, w in _LAST_RESORT.items() if g in gs]
    if scores:
        worlds.sort(key=lambda w: -scores.get(w, 0.0))  # stable: equal scores keep the fixed order
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
