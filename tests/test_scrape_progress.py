import io

from racedata.providers.usat.models import RankingPeriodMeta
from racedata.providers.usat.scrape_progress import ScrapeSummary

from src.usat_rankings.scrape_progress import ConsoleScrapeReporter


def test_console_scrape_reporter_writes_progress_lines():
    buffer = io.StringIO()
    reporter = ConsoleScrapeReporter(stream=buffer)
    meta = RankingPeriodMeta(
        period_id=2241,
        year=2025,
        gender="Male",
        discipline="Triathlon",
        age_group="50-54",
        total_ranked=1015,
    )

    reporter.on_plan(year=2025, discipline="Triathlon", candidate_count=36, skipped_cached=2)
    reporter.on_probe(period_id=2241, probe_index=1, probe_total=34)
    reporter.on_probe_result(period_id=2241, matched=True, meta=meta)
    reporter.on_period_start(meta=meta, period_index=1, period_total=1, estimated_pages=51)
    reporter.on_period_page(
        meta=meta,
        page=1,
        athletes_on_page=20,
        athletes_total=20,
        estimated_pages=51,
    )
    reporter.on_period_complete(meta=meta, athlete_count=1015)
    reporter.on_complete(
        ScrapeSummary(
            year=2025,
            discipline="Triathlon",
            candidate_count=36,
            skipped_cached=2,
            probed_count=34,
            matched_count=1,
            scraped_periods=(meta,),
            total_athletes=1015,
            http_requests=52,
            elapsed_seconds=125.0,
        )
    )

    output = buffer.getvalue()
    assert "USAT scrape plan" in output
    assert "[probe 1/34" in output
    assert "match period 2241" in output
    assert "[period 1/1" in output
    assert "page 1/51" in output
    assert "Scrape complete" in output
    assert "periods scraped: 1" in output
