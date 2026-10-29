import json
from pathlib import Path

from cinesense.domain.models import Movie

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "placeholder_movies.json"


class FixtureProvider:
    """Serves movies from a local JSON fixture (offline development and tests)."""

    def __init__(self, path: Path = DEFAULT_FIXTURE_PATH) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._movies = [Movie.model_validate(item) for item in raw]
        self._by_id = {m.id: m for m in self._movies}

    def list_movies(self) -> list[Movie]:
        return list(self._movies)

    def get_movie(self, movie_id: str) -> Movie | None:
        return self._by_id.get(movie_id)
