import pytest

from cinesense.domain.models import Availability, Movie


@pytest.fixture
def make_movie():
    def _make(**overrides) -> Movie:
        data = {
            "id": "m",
            "title": "Demo-Film",
            "original_language": "en",
            "genres": ["Comedy"],
            "world_ids": ["humor"],
            "runtime_min": 100,
            "ml_rating": 3.6,
            "ml_rating_count": 1000,
            "availability": Availability(),
        }
        data.update(overrides)
        return Movie(**data)

    return _make
