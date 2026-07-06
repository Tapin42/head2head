from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from racedata.providers.ironman.models import RaceFinisher
from racedata.providers.usat.models import RankedAthlete


@dataclass(frozen=True)
class PacesetterResult:
    finisher: RaceFinisher
    prior_year_score: float
    calculated_time_minutes: float


@dataclass(frozen=True)
class RaceScoreEstimate:
    finisher: RaceFinisher
    race_score: float
    par_time_minutes: float


def finish_seconds_to_minutes(seconds: float) -> float:
    return seconds / 60.0


def compute_calculated_time_minutes(finish_seconds: float, prior_year_score: float) -> float:
    return finish_seconds_to_minutes(finish_seconds) * (prior_year_score / 100.0)


def compute_par_time_minutes(calculated_times: list[float]) -> float | None:
    if not calculated_times:
        return None
    sorted_times = sorted(calculated_times)
    count = len(sorted_times)
    if count <= 4:
        trimmed = sorted_times
    else:
        drop = int(count * 0.2)
        trimmed = sorted_times[drop : count - drop]
        if not trimmed:
            trimmed = sorted_times
    return sum(trimmed) / len(trimmed)


def compute_race_score(finish_seconds: float, par_time_minutes: float) -> float:
    finish_minutes = finish_seconds_to_minutes(finish_seconds)
    if finish_minutes <= 0 or par_time_minutes <= 0:
        return 0.0
    return (par_time_minutes / finish_minutes) * 100.0


def build_pacesetter_results(
    finishers: list[RaceFinisher],
    pacesetter_scores: dict[str, RankedAthlete],
    *,
    name_key: Callable[[RaceFinisher], str],
) -> list[PacesetterResult]:
    results: list[PacesetterResult] = []
    for finisher in finishers:
        athlete = pacesetter_scores.get(name_key(finisher))
        if athlete is None:
            continue
        results.append(
            PacesetterResult(
                finisher=finisher,
                prior_year_score=athlete.overall_score,
                calculated_time_minutes=compute_calculated_time_minutes(
                    finisher.finish_seconds,
                    athlete.overall_score,
                ),
            )
        )
    return results


def estimate_race_scores(
    finishers: list[RaceFinisher],
    pacesetter_scores: dict[str, RankedAthlete],
    *,
    name_key: Callable[[RaceFinisher], str],
) -> tuple[float | None, list[RaceScoreEstimate]]:
    pacesetters = build_pacesetter_results(finishers, pacesetter_scores, name_key=name_key)
    par_time = compute_par_time_minutes([p.calculated_time_minutes for p in pacesetters])
    if par_time is None:
        return None, []

    estimates: list[RaceScoreEstimate] = []
    for finisher in finishers:
        estimates.append(
            RaceScoreEstimate(
                finisher=finisher,
                race_score=compute_race_score(finisher.finish_seconds, par_time),
                par_time_minutes=par_time,
            )
        )
    return par_time, estimates
