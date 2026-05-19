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


def test_grid_drops_start_and_expands_display_columns():
    race = Race(event_key="EVENT", display_name="Test Race")
    athletes = [
        AthleteRef(profile_id="A", entry_id="1", name="Seed"),
        AthleteRef(profile_id="B", entry_id="2", name="Other"),
    ]
    splits = {
        "A": [
            _split("START", "Start", 0, 0),
            _split("SWIM", "Swim", 1200, 1200),
            _split("FINISH", "Finish", 3600, 2400),
        ],
        "B": [
            _split("START", "Start", 0, 0),
            _split("SWIM", "Swim", 1500, 1500),
            _split("FINISH", "Finish", 3900, 2400),
        ],
    }
    grid = build_grid_view(race, athletes, splits, baseline_index=0)

    assert [group["label"] for group in grid["column_groups"]] == ["Swim", "Finish"]
    assert grid["column_groups"][1]["leg_label"] == "Run"
    assert len(grid["rows"][0]["display_cells"]) == 4

    swim_clock = grid["rows"][1]["display_cells"][0]
    swim_leg = grid["rows"][1]["display_cells"][1]
    assert swim_clock["kind"] == "clock"
    assert swim_clock["delta"] == "+5:00"
    assert swim_leg["kind"] == "leg"
    assert swim_leg["delta"] == "+5:00"


def test_grid_marks_hidden_columns_and_cells():
    race = Race(event_key="EVENT", display_name="Test Race")
    athletes = [AthleteRef(profile_id="A", entry_id="1", name="Seed")]
    splits = {
        "A": [
            _split("START", "Start", 0, 0),
            _split("RUN1FINISH", "Run 1 - Finish", 1200, 1200),
            _split("RUN1-1", "Run 1.6mi | 2.6km", 1500, 300),
        ]
    }

    grid = build_grid_view(
        race,
        athletes,
        splits,
        hidden_segment_ids={"RUN1-1"},
    )

    assert grid["has_hidden_columns"] is True
    assert [column["hidden_by_default"] for column in grid["columns"]] == [False, True]
    assert [group["hidden_by_default"] for group in grid["column_groups"]] == [False, True]
    assert [cell["hidden_by_default"] for cell in grid["rows"][0]["display_cells"]] == [
        False,
        False,
        True,
        True,
    ]
