from cinesense.domain.models import MoodWorld

# Single source of truth for the six mood worlds (spec §4); tints match the approved mockup.
WORLDS: tuple[MoodWorld, ...] = (
    MoodWorld(
        id="suspense",
        title="Suspense & Mystery",
        kicker="Mystery & Thriller",
        subtitle="Secrets · Suspense · Twists",
        tint="#1b4a6b",
        genres=["Mystery", "Thriller", "Crime"],
    ),
    MoodWorld(
        id="scifi",
        title="Science Fiction",
        kicker="Beyond Reality",
        subtitle="Space · Future · Wonder",
        tint="#8a3fa8",
        genres=["Science Fiction"],
    ),
    MoodWorld(
        id="romance",
        title="Love & Feelings",
        kicker="Feel Everything",
        subtitle="Romantic · Emotional",
        tint="#d98a3a",
        genres=["Romance", "Drama"],
    ),
    MoodWorld(
        id="adventure",
        title="Adventure",
        kicker="Into the Unknown",
        subtitle="Epic journeys · Discovery",
        tint="#5c7a4a",
        genres=["Adventure", "Fantasy"],
    ),
    MoodWorld(
        id="comedy",
        title="Comedy & Feel-Good",
        kicker="Laugh & Escape",
        subtitle="Funny · Relaxed",
        tint="#e0b040",
        genres=["Comedy", "Family", "Animation"],
    ),
    MoodWorld(
        id="action",
        title="Action & Adrenaline",
        kicker="Action & Adrenaline",
        subtitle="Pace · Explosions · Heroes",
        tint="#a8382a",
        genres=["Action"],
    ),
)

_BY_ID = {w.id: w for w in WORLDS}


def get_world(world_id: str) -> MoodWorld | None:
    return _BY_ID.get(world_id)
