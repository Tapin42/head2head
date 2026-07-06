from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

from racedata.providers.usat.models import RankingPeriodMeta
from racedata.providers.usat.scrape_progress import ScrapeProgressCallback, ScrapeSummary


def _format_duration(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    whole = int(seconds + 0.5)
    minutes, secs = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _format_eta(elapsed: float, completed: int, total: int) -> str:
    if completed <= 0 or total <= completed:
        return "—"
    remaining = elapsed / completed * (total - completed)
    return _format_duration(remaining)


@dataclass
class ConsoleScrapeReporter(ScrapeProgressCallback):
    stream: object = sys.stderr
    _started_at: float = field(default_factory=time.monotonic)
    _estimated_requests: int = 0
    _completed_requests: int = 0

    def _write(self, message: str) -> None:
        print(message, file=self.stream, flush=True)

    def on_plan(
        self,
        *,
        year: int,
        discipline: str,
        candidate_count: int,
        skipped_cached: int,
    ) -> None:
        self._started_at = time.monotonic()
        self._write(
            f"USAT scrape plan: {year} {discipline}\n"
            f"  candidate period IDs: {candidate_count}\n"
            f"  already cached (skip): {skipped_cached}\n"
            f"  to probe: {candidate_count - skipped_cached}"
        )

    def on_probe(
        self,
        *,
        period_id: int,
        probe_index: int,
        probe_total: int,
    ) -> None:
        elapsed = time.monotonic() - self._started_at
        eta = _format_eta(elapsed, probe_index - 1, probe_total)
        self._write(
            f"[probe {probe_index}/{probe_total}, ETA {eta}] period {period_id} ..."
        )

    def on_probe_result(
        self,
        *,
        period_id: int,
        matched: bool,
        meta: RankingPeriodMeta | None = None,
        reason: str = "",
    ) -> None:
        if matched and meta is not None:
            pages = max(1, ((meta.total_ranked or 0) + 19) // 20)
            self._estimated_requests += pages
            self._write(
                f"  match period {period_id}: {meta.gender} {meta.age_group} "
                f"({meta.total_ranked or '?'} ranked, ~{pages} page(s))"
            )
            return
        detail = f" ({reason})" if reason else ""
        self._write(f"  skip period {period_id}{detail}")

    def on_period_start(
        self,
        *,
        meta: RankingPeriodMeta,
        period_index: int,
        period_total: int,
        estimated_pages: int,
    ) -> None:
        elapsed = time.monotonic() - self._started_at
        eta = _format_eta(elapsed, period_index - 1, period_total)
        self._write(
            f"[period {period_index}/{period_total}, ETA {eta}] "
            f"{meta.gender} {meta.age_group} (period {meta.period_id}, "
            f"{meta.total_ranked or '?'} ranked)"
        )

    def on_period_page(
        self,
        *,
        meta: RankingPeriodMeta,
        page: int,
        athletes_on_page: int,
        athletes_total: int,
        estimated_pages: int,
    ) -> None:
        self._completed_requests += 1
        elapsed = time.monotonic() - self._started_at
        req_eta = _format_eta(elapsed, self._completed_requests, max(self._estimated_requests, 1))
        target = meta.total_ranked or athletes_total
        self._write(
            f"  page {page}/{estimated_pages}: +{athletes_on_page} athletes "
            f"({athletes_total}/{target}), req ETA {req_eta}"
        )

    def on_period_complete(
        self,
        *,
        meta: RankingPeriodMeta,
        athlete_count: int,
    ) -> None:
        self._write(
            f"  saved period {meta.period_id}: {athlete_count} athletes "
            f"({meta.gender} {meta.age_group})"
        )

    def on_complete(self, summary: ScrapeSummary) -> None:
        self._write(
            "\nScrape complete.\n"
            f"  periods scraped: {len(summary.scraped_periods)}\n"
            f"  athletes stored: {summary.total_athletes}\n"
            f"  HTTP requests:   {summary.http_requests}\n"
            f"  elapsed:         {_format_duration(summary.elapsed_seconds)}\n"
            f"  probed/skipped:  {summary.probed_count} probed, "
            f"{summary.skipped_cached} cached skip, "
            f"{summary.matched_count} matched"
        )
        if summary.scraped_periods:
            self._write("  scraped periods:")
            for period in summary.scraped_periods:
                self._write(
                    f"    {period.period_id}: {period.gender} {period.age_group} "
                    f"({period.total_ranked or '?'} ranked)"
                )
