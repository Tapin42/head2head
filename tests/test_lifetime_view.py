from racedata.lifetime.models import (
    HeadToHeadMatch,
    LifetimeAthleteProfile,
    LifetimeRaceResult,
)
from src.lifetime_view import build_lifetime_compare_view, format_time_delta


def _profile(athlete_id: str, name: str) -> LifetimeAthleteProfile:
    first, _, last = name.partition(" ")
    return LifetimeAthleteProfile(
        provider="usat",
        athlete_id=athlete_id,
        display_name=name,
        first_name=first,
        last_name=last,
        age=50,
        gender="Male",
        location="Wisconsin",
    )


def _result(athlete_id: str, event_id: str, race_id: str, *, date: str = "2025-06-01") -> LifetimeRaceResult:
    return LifetimeRaceResult(
        provider="usat",
        athlete_id=athlete_id,
        event_id=event_id,
        race_id=race_id,
        result_id=f"{athlete_id}-{race_id}",
        event_name="Shared Event",
        race_name="Sprint Tri",
        race_date=date,
        position=10,
        ranking=100.0,
        finish_time="1:00:00.000",
        finish_seconds=3600.0,
    )


def test_format_time_delta():
    assert format_time_delta(120.0) == "+2:00"
    assert format_time_delta(-90.0) == "-1:30"


def test_build_lifetime_compare_view_includes_shared_races_only():
    profile_a = _profile("1", "Joe Navratil")
    profile_b = _profile("2", "Kevin Navratil")
    matches = [
        HeadToHeadMatch(
            event_id="100",
            race_id="200",
            event_name="Shared Event",
            race_name="Sprint Tri",
            race_date="2025-06-01",
            result_a=_result("1", "100", "200"),
            result_b=_result("2", "100", "200", date="2025-06-01"),
        )
    ]
    view = build_lifetime_compare_view(profile_a, profile_b, matches)
    assert view["athlete_a"]["display_name"] == "Joe Navratil"
    assert len(view["rows"]) == 1
    assert view["rows"][0]["event_name"] == "Shared Event"
    assert view["rows"][0]["race_url"].endswith("/events/100/races/200/results")
