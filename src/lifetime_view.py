from __future__ import annotations

from racedata.core.timing import format_hhmmss
from racedata.lifetime.models import HeadToHeadMatch, LifetimeAthleteProfile

USAT_BASE = "https://member.usatriathlon.org"


def format_time_delta(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    whole_seconds = int(round(seconds))
    return format_hhmmss(whole_seconds, signed=True)


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
        "ranking": result.ranking,
        "finish_time": result.finish_time,
    }


def build_lifetime_compare_view(
    profile_a: LifetimeAthleteProfile,
    profile_b: LifetimeAthleteProfile,
    matches: list[HeadToHeadMatch],
) -> dict:
    rows = []
    for match in matches:
        rows.append(
            {
                "event_id": match.event_id,
                "race_id": match.race_id,
                "event_name": match.event_name,
                "race_name": match.race_name,
                "race_date": match.race_date,
                "race_url": f"{USAT_BASE}/events/{match.event_id}/races/{match.race_id}/results",
                "athlete_a": _result_dict(match.result_a),
                "athlete_b": _result_dict(match.result_b),
                "time_delta": format_time_delta(match.time_delta_seconds),
            }
        )
    return {
        "provider": profile_a.provider,
        "athlete_a": _profile_dict(profile_a),
        "athlete_b": _profile_dict(profile_b),
        "rows": rows,
        "match_count": len(rows),
    }
