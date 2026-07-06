from __future__ import annotations

from dataclasses import dataclass

from racedata.providers.ironman.client import IronmanClient
from racedata.providers.mtec.client import MtecClient
from racedata.providers.ironman.models import RaceFinisher
from racedata.providers.usat.rankings_store import UsatRankingsStore

from src.usat_rankings.match import FinisherMatch, MatchStatus, finisher_normalized_name, match_finishers
from src.usat_rankings.score import RaceScoreEstimate, estimate_race_scores


@dataclass(frozen=True)
class MatchReport:
    total_finishers: int
    matched: int
    no_match: int
    ambiguous: int
    matches: tuple[FinisherMatch, ...]


@dataclass(frozen=True)
class EstimateReport:
    par_time_minutes: float | None
    pacesetter_count: int
    match_report: MatchReport
    scores: tuple[RaceScoreEstimate, ...]


def build_match_report(matches: list[FinisherMatch]) -> MatchReport:
    matched = sum(1 for m in matches if m.status == MatchStatus.MATCHED)
    no_match = sum(1 for m in matches if m.status == MatchStatus.NO_MATCH)
    ambiguous = sum(1 for m in matches if m.status == MatchStatus.AMBIGUOUS)
    return MatchReport(
        total_finishers=len(matches),
        matched=matched,
        no_match=no_match,
        ambiguous=ambiguous,
        matches=tuple(matches),
    )


def load_ironman_finishers(race_key: str, *, client: IronmanClient | None = None) -> list[RaceFinisher]:
    ironman = client or IronmanClient()
    return ironman.fetch_race_by_key(race_key)


def load_mtec_finishers(race_key: str, *, client: MtecClient | None = None) -> list[RaceFinisher]:
    mtec = client or MtecClient()
    return mtec.fetch_race_by_key(race_key)


def run_match_report(
    finishers: list[RaceFinisher],
    store: UsatRankingsStore,
    *,
    pacesetter_year: int,
    discipline: str = "Triathlon",
) -> MatchReport:
    matches = match_finishers(
        finishers,
        store,
        pacesetter_year=pacesetter_year,
        discipline=discipline,
    )
    return build_match_report(matches)


def run_estimate(
    finishers: list[RaceFinisher],
    store: UsatRankingsStore,
    *,
    pacesetter_year: int,
    discipline: str = "Triathlon",
) -> EstimateReport:
    matches = match_finishers(
        finishers,
        store,
        pacesetter_year=pacesetter_year,
        discipline=discipline,
    )
    match_report = build_match_report(matches)

    pacesetter_scores = {
        finisher_normalized_name(match.finisher): match.pacesetter
        for match in matches
        if match.status == MatchStatus.MATCHED and match.pacesetter is not None
    }
    pacesetter_finishers = [m.finisher for m in matches if m.status == MatchStatus.MATCHED]
    par_time, scores = estimate_race_scores(
        finishers,
        pacesetter_scores,
        name_key=finisher_normalized_name,
    )
    return EstimateReport(
        par_time_minutes=par_time,
        pacesetter_count=len(pacesetter_finishers),
        match_report=match_report,
        scores=tuple(scores),
    )
