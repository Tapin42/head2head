from __future__ import annotations

from src.usat_rankings.estimate import EstimateReport, MatchReport
from src.usat_rankings.match import FinisherMatch, MatchStatus
from src.usat_rankings.score import RaceScoreEstimate


def format_match_report(report: MatchReport) -> str:
    lines = [
        f"Total finishers: {report.total_finishers}",
        f"Exact name match:  {report.matched} ({_pct(report.matched, report.total_finishers)})",
        f"No match:          {report.no_match} ({_pct(report.no_match, report.total_finishers)})",
        f"Ambiguous:         {report.ambiguous} ({_pct(report.ambiguous, report.total_finishers)})",
    ]
    if report.ambiguous:
        lines.append("")
        lines.append("Ambiguous matches:")
        for match in report.matches:
            if match.status != MatchStatus.AMBIGUOUS:
                continue
            lines.append(_format_ambiguous(match))
    return "\n".join(lines)


def format_estimate_report(
    report: EstimateReport,
    *,
    limit: int = 25,
    name_query: str | None = None,
) -> str:
    lines = [
        format_match_report(report.match_report),
        "",
        f"Pacesetters used: {report.pacesetter_count}",
        f"Par time (minutes): {report.par_time_minutes:.3f}" if report.par_time_minutes else "Par time: unavailable",
    ]
    if not report.scores:
        return "\n".join(lines)

    ranked = sorted(report.scores, key=lambda item: item.race_score, reverse=True)
    if name_query:
        matches = [item for item in ranked if _finisher_name_matches(item.finisher, name_query)]
        lines.extend(["", f"Lookup results for {name_query!r} ({len(matches)} finisher(s)):"])
        if not matches:
            lines.append("  (no finishers matched — try last name only, or check spelling)")
        for item in matches:
            lines.append(_format_score_line(item))
        return "\n".join(lines)

    lines.extend(["", f"Top {min(limit, len(ranked))} estimated race scores:"])
    for item in ranked[:limit]:
        lines.append(_format_score_line(item))
    return "\n".join(lines)


def _format_score_line(item: RaceScoreEstimate) -> str:
    finisher = item.finisher
    return (
        f"  {item.race_score:7.3f}  {finisher.display_name:<28} "
        f"{finisher.finish_time:<10} {finisher.state or finisher.country}"
    )


def _finisher_name_matches(finisher, query: str) -> bool:
    needle = query.casefold()
    for field in (finisher.display_name, finisher.first_name, finisher.last_name):
        if needle in field.casefold():
            return True
    return False


def _format_ambiguous(match: FinisherMatch) -> str:
    finisher = match.finisher
    candidate_text = "; ".join(
        f"{c.last_name}, {c.first_name} ({c.state}) score={c.overall_score:.3f}"
        for c in match.candidates
    )
    return f"  {finisher.display_name} ({finisher.state}): {candidate_text}"


def _pct(part: int, whole: int) -> str:
    if whole == 0:
        return "0.0%"
    return f"{100.0 * part / whole:.1f}%"
