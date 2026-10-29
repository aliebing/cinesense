from cinesense.domain.models import MoodWorld

# Single source of truth for the six mood worlds (spec §4); tints match the approved mockup.
WORLDS: tuple[MoodWorld, ...] = (
    MoodWorld(
        id="spannung",
        title_de="Spannung & Rätsel",
        kicker="Mystery & Thriller",
        subtitle_de="Geheimnisse · Spannung · Wendungen",
        tint="#1b4a6b",
        genres=["Mystery", "Thriller", "Crime"],
    ),
    MoodWorld(
        id="scifi",
        title_de="Science-Fiction",
        kicker="Beyond Reality",
        subtitle_de="Weltraum · Zukunft · Staunen",
        tint="#8a3fa8",
        genres=["Science Fiction"],
    ),
    MoodWorld(
        id="gefuehl",
        title_de="Liebe & Gefühle",
        kicker="Feel Everything",
        subtitle_de="Romantisch · Emotional",
        tint="#d98a3a",
        genres=["Romance", "Drama"],
    ),
    MoodWorld(
        id="abenteuer",
        title_de="Abenteuer",
        kicker="Into the Unknown",
        subtitle_de="Epische Reisen · Entdeckungen",
        tint="#5c7a4a",
        genres=["Adventure", "Fantasy"],
    ),
    MoodWorld(
        id="humor",
        title_de="Humor & Leichtigkeit",
        kicker="Laugh & Escape",
        subtitle_de="Lustig · Entspannt",
        tint="#e0b040",
        genres=["Comedy", "Family", "Animation"],
    ),
    MoodWorld(
        id="action",
        title_de="Action & Adrenalin",
        kicker="Action & Adrenalin",
        subtitle_de="Tempo · Explosionen · Helden",
        tint="#a8382a",
        genres=["Action"],
    ),
)

_BY_ID = {w.id: w for w in WORLDS}


def get_world(world_id: str) -> MoodWorld | None:
    return _BY_ID.get(world_id)
