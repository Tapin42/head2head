from racedata.core.models import AthleteRef, Race

from src.view_models import build_grid_view


def test_build_grid_view_zero_athletes():
    race = Race(event_key="146818", display_name="Empty Race", provider="sportstats")
    grid = build_grid_view(race, [], {})
    assert grid["rows"] == []
    assert grid["columns"] == []
    assert grid["race_title"] == "Empty Race"
