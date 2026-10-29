"""Generate the fictional, clearly labelled placeholder film set used until real TMDB data exists.

Run: uv run python scripts/make_placeholder_fixtures.py
"""

import json
from pathlib import Path

from cinesense.domain.worlds import WORLDS

OUT = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "placeholder_movies.json"
PROVIDERS = [["Netflix"], ["Amazon Prime Video"], ["Disney Plus"], ["Netflix", "Disney Plus"], ["WOW"]]
LANGS = ["en", "en", "en", "de", "en", "en", "fr", "en", "en", "en"]


def build() -> list[dict]:
    movies = []
    for n in range(1, 49):
        world = WORLDS[(n - 1) % len(WORLDS)]
        second = WORLDS[n % len(WORLDS)] if n % 4 == 0 else None
        genres = list(world.genres[:2])
        if n % 11 == 0:
            genres.append("Horror")
        in_cinema = n % 3 == 0
        streaming = PROVIDERS[n % len(PROVIDERS)] if n % 3 != 0 and n % 7 != 0 else []
        movies.append(
            {
                "id": f"demo-{n:02d}",
                "title": f"Demo-Film {n:02d}",
                "year": 1995 + (n * 7) % 31,
                "runtime_min": 85 + (n * 13) % 91,
                "original_language": LANGS[n % len(LANGS)],
                "genres": genres,
                "world_ids": [world.id] + ([second.id] if second else []),
                "overview": (
                    f"Platzhalter für einen Film aus der Welt „{world.title_de}“. Echte Daten folgen."
                ),
                "poster_url": None if n == 7 else f"https://picsum.photos/seed/cs-poster-{n}/300/450",
                "backdrop_url": None if n == 7 else f"https://picsum.photos/seed/cs-backdrop-{n}/1280/720",
                "youtube_key": None if n % 6 == 0 else "placeholder",
                "vote_average": round(5.0 + ((n * 37) % 40) / 10, 1),
                "vote_count": [5, 120, 900, 4000, 20000][n % 5],
                "age_rating_de": ["0", "6", "12", "16"][n % 4],
                "availability": {"in_cinema_de": in_cinema, "streaming_flatrate_de": streaming},
                "is_placeholder": True,
            }
        )
    return movies


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
