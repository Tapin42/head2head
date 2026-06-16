from __future__ import annotations

import re
from datetime import datetime

from racedata.core.timing import format_hhmmss
from racedata.lifetime.models import HeadToHeadMatch, LifetimeAthleteProfile

USAT_BASE = "https://member.usatriathlon.org"

_DATE_FORMATS_WITH_YEAR = ("%Y-%m-%d", "%b %d, %Y", "%b %d,%Y", "%B %d, %Y", "%B %d,%Y")
_DATE_FORMATS_MONTH_DAY = ("%b %d", "%B %d")


def format_time_delta(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    whole_seconds = int(round(seconds))
    return format_hhmmss(whole_seconds, signed=True)


def format_display_time(finish_time: str, finish_seconds: float | None = None) -> str:
    seconds = finish_seconds
    if seconds is None and finish_time:
        parts = finish_time.strip().split(":")
        try:
            if len(parts) == 3:
                seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                seconds = float(parts[0]) * 60 + float(parts[1])
        except ValueError:
            seconds = None
    if seconds is None:
        return finish_time or "—"
    return format_hhmmss(int(seconds + 0.5))


def format_display_ranking(ranking: float | None) -> str | None:
    if ranking is None:
        return None
    return f"{ranking:.3f}".rstrip("0").rstrip(".")


def _parse_race_date(race_date: str, event_name: str = "") -> tuple[int, int, int]:
    cleaned = re.sub(r"^\w+,\s+", "", race_date.strip())
    for fmt in _DATE_FORMATS_WITH_YEAR:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return (parsed.year, parsed.month, parsed.day)
        except ValueError:
            continue
    for fmt in _DATE_FORMATS_MONTH_DAY:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            year_match = re.search(r"\b(20\d{2})\b", event_name)
            year = int(year_match.group(1)) if year_match else 0
            return (year, parsed.month, parsed.day)
        except ValueError:
            continue
    return (0, 0, 0)


def _race_date_iso(race_date: str, event_name: str = "") -> str:
    year, month, day = _parse_race_date(race_date, event_name)
    if year and month and day:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def _profile_dict(profile: LifetimeAthleteProfile) -> dict:
    return {
        "athlete_id": profile.athlete_id,
        "display_name": profile.display_name,
        "age": profile.age,
        "gender": profile.gender,
        "location": profile.location,
    }


def _result_dict(result) -> dict:
    return {
        "position": result.position,
        "ranking": format_display_ranking(result.ranking),
        "finish_time": format_display_time(result.finish_time, result.finish_seconds),
    }


def _match_row(match: HeadToHeadMatch) -> dict:
    delta_seconds = match.time_delta_seconds
    winner_a = delta_seconds is not None and delta_seconds > 0
    winner_b = delta_seconds is not None and delta_seconds < 0
    loser_delta_a = None
    loser_delta_b = None
    if delta_seconds is not None and delta_seconds != 0:
        if delta_seconds > 0:
            loser_delta_b = format_time_delta(delta_seconds)
        else:
            loser_delta_a = format_time_delta(-delta_seconds)

    return {
        "event_id": match.event_id,
        "race_id": match.race_id,
        "event_name": match.event_name,
        "race_name": match.race_name,
        "race_date": match.race_date,
        "date_sort": _race_date_iso(match.race_date, match.event_name),
        "race_url": f"{USAT_BASE}/events/{match.event_id}/races/{match.race_id}/results",
        "athlete_a": _result_dict(match.result_a),
        "athlete_b": _result_dict(match.result_b),
        "winner_a": winner_a,
        "winner_b": winner_b,
        "loser_delta_a": loser_delta_a,
        "loser_delta_b": loser_delta_b,
    }


def build_lifetime_compare_view(
    profile_a: LifetimeAthleteProfile,
    profile_b: LifetimeAthleteProfile,
    matches: list[HeadToHeadMatch],
) -> dict:
    sorted_matches = sorted(
        matches,
        key=lambda match: _parse_race_date(match.race_date, match.event_name),
        reverse=True,
    )
    rows = [_match_row(match) for match in sorted_matches]
    return {
        "provider": profile_a.provider,
        "athlete_a": _profile_dict(profile_a),
        "athlete_b": _profile_dict(profile_b),
        "rows": rows,
        "match_count": len(rows),
    }
