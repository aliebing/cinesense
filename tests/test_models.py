from cinesense.domain.worlds import WORLDS, get_world


def test_six_worlds_in_spec_order():
    assert [w.id for w in WORLDS] == ["spannung", "scifi", "gefuehl", "abenteuer", "humor", "action"]
    assert [w.title_de for w in WORLDS] == [
        "Spannung & Rätsel",
        "Science-Fiction",
        "Liebe & Gefühle",
        "Abenteuer",
        "Humor & Leichtigkeit",
        "Action & Adrenalin",
    ]


def test_world_tints_match_mockup():
    assert {w.id: w.tint for w in WORLDS} == {
        "spannung": "#1b4a6b",
        "scifi": "#8a3fa8",
        "gefuehl": "#d98a3a",
        "abenteuer": "#5c7a4a",
        "humor": "#e0b040",
        "action": "#a8382a",
    }


def test_get_world_unknown_returns_none():
    assert get_world("horror") is None
    assert get_world("scifi").title_de == "Science-Fiction"
