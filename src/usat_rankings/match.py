from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from racedata.providers.ironman.models import RaceFinisher
from racedata.providers.usat.models import RankedAthlete
from racedata.providers.usat.rankings_parse import normalize_ranking_name
from racedata.providers.usat.rankings_store import UsatRankingsStore

STATE_ABBREV = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC",
}


class MatchStatus(str, Enum):
    MATCHED = "matched"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class FinisherMatch:
    finisher: RaceFinisher
    status: MatchStatus
    pacesetter: RankedAthlete | None = None
    candidates: tuple[RankedAthlete, ...] = ()


def normalize_state(value: str) -> str:
    cleaned = re.sub(r"[^A-Z ]", "", value.upper()).strip()
    if len(cleaned) <= 3 and cleaned.isalpha():
        return cleaned
    return STATE_ABBREV.get(cleaned, cleaned)


def finisher_normalized_name(finisher: RaceFinisher) -> str:
    return normalize_ranking_name(finisher.last_name, finisher.first_name)


def states_match(finisher_state: str, ranked_state: str) -> bool:
    left = normalize_state(finisher_state)
    right = normalize_state(ranked_state)
    if not left or not right:
        return False
    return left == right or left in right or right in left


def match_finisher_to_pacesetter(
    finisher: RaceFinisher,
    candidates: list[RankedAthlete],
) -> FinisherMatch:
    if not candidates:
        return FinisherMatch(finisher=finisher, status=MatchStatus.NO_MATCH)

    if len(candidates) == 1:
        return FinisherMatch(
            finisher=finisher,
            status=MatchStatus.MATCHED,
            pacesetter=candidates[0],
        )

    by_state = [c for c in candidates if states_match(finisher.state, c.state)]
    if len(by_state) == 1:
        return FinisherMatch(
            finisher=finisher,
            status=MatchStatus.MATCHED,
            pacesetter=by_state[0],
            candidates=tuple(candidates),
        )

    return FinisherMatch(
        finisher=finisher,
        status=MatchStatus.AMBIGUOUS,
        candidates=tuple(candidates),
    )


def match_finishers(
    finishers: list[RaceFinisher],
    store: UsatRankingsStore,
    *,
    pacesetter_year: int,
    discipline: str = "Triathlon",
) -> list[FinisherMatch]:
    index: dict[str, list[RankedAthlete]] = {}
    for athlete in store.all_athletes_for_year(year=pacesetter_year, discipline=discipline):
        index.setdefault(athlete.normalized_name, []).append(athlete)

    results: list[FinisherMatch] = []
    for finisher in finishers:
        key = finisher_normalized_name(finisher)
        results.append(match_finisher_to_pacesetter(finisher, index.get(key, [])))
    return results
