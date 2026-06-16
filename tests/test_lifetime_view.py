from racedata.lifetime.models import (
    HeadToHeadMatch,
    LifetimeAthleteProfile,
    LifetimeRaceResult,
)
from src.lifetime_view import (
    _parse_race_date,
    build_lifetime_compare_view,
    format_display_ranking,
    format_display_time,
    format_time_delta,
)


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


def test_format_display_time_rounds_to_nearest_second():
    assert format_display_time("2:48:16.000", 10096.0) == "2:48:16"
    assert format_display_time("2:25:10.5", 8710.5) == "2:25:11"
    assert format_display_time("2:32:25.971", 9145.971) == "2:32:26"
    assert format_display_time("1:00:00.000", 3600.0) == "1:00:00"


def test_format_display_ranking_strips_trailing_zeroes():
    assert format_display_ranking(83.8) == "83.8"
    assert format_display_ranking(95.286) == "95.286"
    assert format_display_ranking(100.0) == "100"


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
    assert view["rows"][0]["date_sort"] == "2025-06-01"
    assert view["rows"][0]["athlete_a"]["finish_time"] == "1:00:00"
    assert view["rows"][0]["athlete_a"]["ranking"] == "100"


def test_build_lifetime_compare_view_sorts_by_date_descending():
    profile_a = _profile("1", "Joe Navratil")
    profile_b = _profile("2", "Kevin Navratil")
    matches = [
        HeadToHeadMatch(
            event_id="100",
            race_id="200",
            event_name="Older Event",
            race_name="Sprint Tri",
            race_date="Jun 25, 2023",
            result_a=_result("1", "100", "200", date="Jun 25, 2023"),
            result_b=_result("2", "100", "200", date="Jun 25, 2023"),
        ),
        HeadToHeadMatch(
            event_id="101",
            race_id="201",
            event_name="Newer Event",
            race_name="Sprint Tri",
            race_date="Aug 9, 2025",
            result_a=_result("1", "101", "201", date="Aug 9, 2025"),
            result_b=_result("2", "101", "201", date="Aug 9, 2025"),
        ),
    ]
    view = build_lifetime_compare_view(profile_a, profile_b, matches)
    assert [row["race_date"] for row in view["rows"]] == ["Aug 9, 2025", "Jun 25, 2023"]


def test_parse_race_date_handles_usat_formats():
    assert _parse_race_date("Aug 9, 2025") == (2025, 8, 9)
    assert _parse_race_date("Sat, May 16", "2025 Pleasant Prairie Triathlon") == (2025, 5, 16)


def test_build_lifetime_compare_view_marks_winner_and_loser_delta():
    profile_a = _profile("1", "Joe Navratil")
    profile_b = _profile("2", "Kevin Navratil")
    result_a = _result("1", "100", "200")
    result_b = LifetimeRaceResult(
        provider="usat",
        athlete_id="2",
        event_id="100",
        race_id="200",
        result_id="2-200",
        event_name="Shared Event",
        race_name="Sprint Tri",
        race_date="2025-06-01",
        position=11,
        ranking=110.0,
        finish_time="1:02:00.000",
        finish_seconds=3720.0,
    )
    matches = [
        HeadToHeadMatch(
            event_id="100",
            race_id="200",
            event_name="Shared Event",
            race_name="Sprint Tri",
            race_date="2025-06-01",
            result_a=result_a,
            result_b=result_b,
        )
    ]
    view = build_lifetime_compare_view(profile_a, profile_b, matches)
    row = view["rows"][0]
    assert row["winner_a"] is True
    assert row["winner_b"] is False
    assert row["loser_delta_b"] == "+2:00"
    assert row["loser_delta_a"] is None
