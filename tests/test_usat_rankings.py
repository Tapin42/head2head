import pytest

from racedata.providers.ironman.models import RaceFinisher
from racedata.providers.usat.models import RankedAthlete

from src.usat_rankings.match import (
    MatchStatus,
    finisher_normalized_name,
    match_finisher_to_pacesetter,
    match_finishers,
    states_match,
)
from src.usat_rankings.score import (
    compute_calculated_time_minutes,
    compute_par_time_minutes,
    compute_race_score,
    estimate_race_scores,
)


def _finisher(**kwargs) -> RaceFinisher:
    defaults = dict(
        event_key="test",
        bib=1,
        first_name="Peter",
        last_name="Christensen",
        display_name="Peter Christensen",
        gender="Male",
        age_group="M50-54",
        city="Madison",
        state="WI",
        country="United States",
        finish_time="4:30:55",
        finish_seconds=4 * 3600 + 30 * 60 + 55,
        overall_rank=1,
        age_group_rank=1,
    )
    defaults.update(kwargs)
    return RaceFinisher(**defaults)


def _ranked(**kwargs) -> RankedAthlete:
    defaults = dict(
        period_id=2241,
        rank=2,
        last_name="Christensen",
        first_name="Peter",
        normalized_name="CHRISTENSEN|PETER",
        age=52,
        state="Wisconsin",
        overall_score=107.345,
    )
    defaults.update(kwargs)
    return RankedAthlete(**defaults)


def test_states_match_abbrev_and_full():
    assert states_match("WI", "Wisconsin")
    assert states_match("Wisconsin", "WI")


def test_match_single_candidate():
    result = match_finisher_to_pacesetter(_finisher(), [_ranked()])
    assert result.status == MatchStatus.MATCHED
    assert result.pacesetter is not None


def test_match_ambiguous_without_state():
    candidates = [
        _ranked(state="Wisconsin"),
        _ranked(state="Minnesota", rank=3, overall_score=95.0),
    ]
    result = match_finisher_to_pacesetter(_finisher(state=""), candidates)
    assert result.status == MatchStatus.AMBIGUOUS


def test_match_resolves_by_state():
    candidates = [
        _ranked(state="Wisconsin"),
        _ranked(state="Minnesota", rank=3, overall_score=95.0),
    ]
    result = match_finisher_to_pacesetter(_finisher(state="WI"), candidates)
    assert result.status == MatchStatus.MATCHED
    assert result.pacesetter.state == "Wisconsin"


def test_christensen_rockford_2025_score():
    finisher = _finisher()
    ranked = _ranked()
    calculated = compute_calculated_time_minutes(finisher.finish_seconds, ranked.overall_score)
    par_time = compute_par_time_minutes([calculated])
    score = compute_race_score(finisher.finish_seconds, par_time)
    assert score == pytest.approx(107.345, rel=1e-4)


def test_par_time_trims_outliers():
    values = [80.0, 85.0, 90.0, 95.0, 100.0, 200.0]
    par = compute_par_time_minutes(values)
    assert par == pytest.approx((85.0 + 90.0 + 95.0 + 100.0) / 4)


def test_estimate_race_scores_returns_all_finishers():
    pacesetter = _finisher()
    other = _finisher(first_name="Other", last_name="Athlete", display_name="Other Athlete")
    scores = {
        finisher_normalized_name(pacesetter): _ranked(),
    }
    par_time, estimates = estimate_race_scores(
        [pacesetter, other],
        scores,
        name_key=finisher_normalized_name,
    )
    assert par_time is not None
    assert len(estimates) == 2


def test_match_finishers_against_store(tmp_path):
    from pathlib import Path

    from racedata.providers.usat.rankings_parse import parse_period_meta, parse_ranking_period_page
    from racedata.providers.usat.rankings_store import UsatRankingsStore

    fixture = (
        Path(__file__).resolve().parents[1]
        / ".."
        / "racedata"
        / "tests"
        / "fixtures"
        / "usat_ranking_period_2241_p1.html"
    ).resolve()
    html = fixture.read_text(encoding="utf-8")
    meta = parse_period_meta(html, period_id=2241)
    athletes = parse_ranking_period_page(html, period_id=2241)

    store = UsatRankingsStore(tmp_path / "rankings.db")
    store.save_period(meta, athletes)

    finisher = _finisher()
    matches = match_finishers([finisher], store, pacesetter_year=2025)
    store.close()

    assert len(matches) == 1
    assert matches[0].status == MatchStatus.MATCHED
    assert matches[0].pacesetter.overall_score == pytest.approx(107.345)
