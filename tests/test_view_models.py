from racedata.core.models import AthleteRef, Race, SegmentSplit
from src.view_models import build_grid_view


def _split(segment_id: str, label: str, clock: int, leg: int) -> SegmentSplit:
    return SegmentSplit(
        segment_id=segment_id,
        label=label,
        clock_time=f"{clock // 60}:{clock % 60:02d}",
        clock_seconds=clock,
        leg_time=f"{leg // 60}:{leg % 60:02d}",
        leg_seconds=leg,
    )


def test_grid_row_zero_is_baseline_without_deltas():
    race = Race(event_key="EVENT", display_name="Test Race")
    athletes = [
        AthleteRef(profile_id="A", entry_id="1", name="Seed"),
        AthleteRef(profile_id="B", entry_id="2", name="Other"),
    ]
    splits = {
        "A": [_split("SWIM", "Swim", 1200, 1200)],
        "B": [_split("SWIM", "Swim", 1500, 1500)],
    }
    grid = build_grid_view(race, athletes, splits, baseline_index=0)
    assert grid["rows"][0]["is_baseline"] is True
    assert grid["rows"][0]["cells"][0]["clock_delta"] == "—"
    assert grid["rows"][1]["cells"][0]["clock_delta"] == "+5:00"
    assert grid["rows"][1]["cells"][0]["leg_delta"] == "+5:00"


def test_grid_includes_race_title():
    race = Race(event_key="EVENT", display_name="Venice 70.3")
    grid = build_grid_view(race, [], {})
    assert grid["race_title"] == "Venice 70.3"
