"""Offline provider over a JSON fixture (tests and development without keys)."""

import difflib
import json
from pathlib import Path

import numpy as np

from cinesense.domain.models import Movie
from cinesense.recommend.tags import tag_match

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"
DEFAULT_FIXTURE_PATH = FIXTURE_DIR / "movies.json"
LEGACY_FIXTURE_PATH = FIXTURE_DIR / "placeholder_movies.json"


class FixtureProvider:
    """Fixture format: either a list of movies (legacy) or {"tags": [...], "movies": [...]} where each
    movie may carry "tag_vector_sparse": {idx: relevance} and "people": [{"name", "role"}]."""

    def __init__(self, path: Path | None = None) -> None:
        path = path or (DEFAULT_FIXTURE_PATH if DEFAULT_FIXTURE_PATH.exists() else LEGACY_FIXTURE_PATH)
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw["movies"] if isinstance(raw, dict) else raw
        self._tags: list[str] = raw.get("tags", []) if isinstance(raw, dict) else []
        self._movies = [
            Movie.model_validate({k: v for k, v in i.items() if k not in ("tag_vector_sparse", "people")})
            for i in items
        ]
        self._by_id = {m.id: m for m in self._movies}
        self._vectors: dict[str, np.ndarray] = {}
        self._people: dict[str, list[tuple[str, str]]] = {}
        for i in items:
            if sparse := i.get("tag_vector_sparse"):
                v = np.zeros(1128, dtype=np.float32)
                for idx, rel in sparse.items():
                    v[int(idx)] = rel
                self._vectors[i["id"]] = v
            self._people[i["id"]] = [(p["name"], p["role"]) for p in i.get("people", [])]

    def list_movies(self) -> list[Movie]:
        return [m.model_copy(deep=True) for m in self._movies]

    def get_movie(self, movie_id: str) -> Movie | None:
        m = self._by_id.get(movie_id)
        return m.model_copy(deep=True) if m else None

    def get_many(self, ids: list[str]) -> list[Movie]:
        return [self._by_id[i].model_copy(deep=True) for i in ids if i in self._by_id]

    def update_images(self, movie_id, poster=None, horizontal=None, backdrop=None) -> None:
        m = self._by_id.get(movie_id)
        if m is not None:
            m.poster_url = m.poster_url or poster
            m.horizontal_poster_url = m.horizontal_poster_url or horizontal
            m.backdrop_url = m.backdrop_url or backdrop
            m.images_checked = True

    def list_tags(self) -> list[str]:
        return list(self._tags)

    def tag_vectors(self, ids: list[str]) -> np.ndarray:
        out = np.full((len(ids), 1128), np.nan, dtype=np.float32)
        for row, film_id in enumerate(ids):
            if film_id in self._vectors:
                out[row] = self._vectors[film_id]
        return out

    def tag_search(self, weights, must, exclude, must_threshold=0.6, not_threshold=0.5, limit=500):
        ids = [i for i in self._vectors if all(self._vectors[i][t] >= must_threshold for t in must)]
        hidden = [i for i in ids if any(self._vectors[i][t] >= not_threshold for t in exclude)]
        ids = [i for i in ids if i not in hidden]
        if not ids:
            return [], len(hidden)
        sims = tag_match(weights, np.stack([self._vectors[i] for i in ids]))
        ranked = sorted(zip(ids, sims.tolist(), strict=True), key=lambda x: x[1], reverse=True)[:limit]
        return ranked, len(hidden)

    def semantic_search(self, query_embedding, k: int = 20):
        return []

    def search_title(self, q: str, limit: int = 200) -> dict[str, float]:
        out = {}
        for m in self._movies:
            s = difflib.SequenceMatcher(None, q.lower(), m.title.lower()).ratio()
            if s >= 0.6 or q.lower() in m.title.lower():
                out[m.id] = max(s, 0.5)
        return dict(sorted(out.items(), key=lambda x: x[1], reverse=True)[:limit])

    def search_person(self, q: str, role: str = "any", limit: int = 400):
        scores, names = {}, {}
        for film_id, people in self._people.items():
            for name, r in people:
                if role != "any" and r != role:
                    continue
                s = difflib.SequenceMatcher(None, q.lower(), name.lower()).ratio()
                if s >= 0.75 and s > scores.get(film_id, 0):
                    scores[film_id], names[film_id] = s, name
        return scores, names

    def upsert_live(self, movies: list[Movie]) -> None:
        for m in movies:
            if m.id not in self._by_id:
                self._movies.append(m)
                self._by_id[m.id] = m
