from cinesense.domain.worlds import WORLDS, get_world


def test_six_worlds_in_spec_order():
    assert [w.id for w in WORLDS] == ["suspense", "scifi", "romance", "adventure", "comedy", "action"]
    assert [w.title for w in WORLDS] == [
        "Suspense & Mystery",
        "Science Fiction",
        "Love & Feelings",
        "Adventure",
        "Comedy & Feel-Good",
        "Action & Adrenaline",
    ]


def test_world_tints_match_mockup():
    assert {w.id: w.tint for w in WORLDS} == {
        "suspense": "#1b4a6b",
        "scifi": "#8a3fa8",
        "romance": "#d98a3a",
        "adventure": "#5c7a4a",
        "comedy": "#e0b040",
        "action": "#a8382a",
    }


def test_get_world_unknown_returns_none():
    assert get_world("horror") is None
    assert get_world("scifi").title == "Science Fiction"


def test_subscription_services_unique_and_subscription_only():
    from cinesense.domain.models import Availability, StreamingOption

    a = Availability(
        streaming_de=[
            StreamingOption(service="Netflix", type="subscription"),
            StreamingOption(service="Netflix", type="subscription"),
            StreamingOption(service="Apple TV", type="rent"),
        ]
    )
    assert a.subscription_services == ["Netflix"]


def test_streaming_unknown_is_none():
    from cinesense.domain.models import Availability

    assert Availability().streaming_de is None
    assert Availability().subscription_services == []
