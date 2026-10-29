from cinesense.domain.models import Availability, MovieQuery, StreamingOption
from cinesense.recommend.filters import apply_filters


def ids(movies):
    return [m.id for m in movies]


def test_excludes_horror_case_insensitive(make_movie):
    ms = [make_movie(id="a", genres=["Horror"]), make_movie(id="b", genres=["Comedy"])]
    assert ids(apply_filters(ms, MovieQuery(exclude_genres=["horror"]))) == ["b"]


def test_stream_means_subscription_only(make_movie):
    rent = [StreamingOption(service="Apple TV", type="rent")]
    sub = [StreamingOption(service="Netflix", type="subscription")]
    ms = [
        make_movie(id="a", availability=Availability(in_cinema_de=True, streaming_de=rent)),
        make_movie(id="b", availability=Availability(in_cinema_de=False, streaming_de=sub)),
    ]
    assert ids(apply_filters(ms, MovieQuery(availability="stream"))) == ["b"]
    assert ids(apply_filters(ms, MovieQuery(availability="cinema"))) == ["a"]


def test_unknown_runtime_is_kept(make_movie):
    ms = [make_movie(id="a", runtime_min=None), make_movie(id="b", runtime_min=150)]
    assert ids(apply_filters(ms, MovieQuery(max_runtime_min=120))) == ["a"]


def test_world_language_and_vote_count(make_movie):
    ms = [
        make_movie(id="a", world_ids=["action"], original_language="en", ml_rating_count=50),
        make_movie(id="b", world_ids=["action"], original_language="de", ml_rating_count=5000),
        make_movie(id="c", world_ids=["humor"], original_language="en", ml_rating_count=5000),
        make_movie(id="d", world_ids=["action"], original_language="en", ml_rating_count=5000),
    ]
    q = MovieQuery(world_id="action", original_language="en", min_rating_count=100)
    assert ids(apply_filters(ms, q)) == ["d"]
