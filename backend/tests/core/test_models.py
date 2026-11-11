from cinesense.core.worlds import WORLDS, get_world


def test_seven_worlds_in_order():
    assert [w.id for w in WORLDS] == ["suspense", "scifi", "romance", "adventure", "comedy", "action", "drama"]
    assert [w.title for w in WORLDS] == [
        "Suspense & Mystery",
        "Science Fiction",
        "Love & Feelings",
        "Adventure",
        "Comedy & Feel-Good",
        "Action & Adrenaline",
        "Drama & Life",
    ]


def test_world_tints_match_mockup():
    assert {w.id: w.tint for w in WORLDS} == {
        "suspense": "#1b4a6b",
        "scifi": "#8a3fa8",
        "romance": "#d98a3a",
        "adventure": "#5c7a4a",
        "comedy": "#e0b040",
        "action": "#a8382a",
        "drama": "#7a5c4a",
    }


def test_get_world_unknown_returns_none():
    assert get_world("horror") is None
    assert get_world("scifi").title == "Science Fiction"


def test_subscription_services_unique_and_subscription_only():
    from cinesense.core.models import Availability, StreamingOption

    a = Availability(
        streaming_de=[
            StreamingOption(service="Netflix", type="subscription"),
            StreamingOption(service="Netflix", type="subscription"),
            StreamingOption(service="Apple TV", type="rent"),
        ]
    )
    assert a.subscription_services == ["Netflix"]


def test_streaming_unknown_is_none():
    from cinesense.core.models import Availability

    assert Availability().streaming_de is None
    assert Availability().subscription_services == []


def test_free_offers_count_as_streaming_at_no_extra_cost():
    from cinesense.core.models import Availability, StreamingOption

    a = Availability(
        streaming_de=[
            StreamingOption(service="Pluto TV", type="free"),
            StreamingOption(service="Prime Video", type="addon"),
            StreamingOption(service="Apple TV", type="buy"),
        ]
    )
    assert a.subscription_services == ["Pluto TV"]


def test_service_names_are_normalised():
    from cinesense.core.models import canonical_service

    assert canonical_service("Amazon Prime") == "Prime Video"
    assert canonical_service("prime") == "Prime Video"
    assert canonical_service("netflix") == "Netflix"
    assert canonical_service("Disney Plus") == "Disney+"
    assert canonical_service("Foo TV") is None


def test_streams_on_named_services():
    from cinesense.core.models import Availability, StreamingOption

    a = Availability(
        streaming_de=[
            StreamingOption(service="Netflix", type="subscription"),
            StreamingOption(service="Prime Video", type="rent"),
        ]
    )
    assert a.streams_on([]) and a.streams_on(["Netflix"])
    assert not a.streams_on(["Prime Video"])  # renting costs extra
