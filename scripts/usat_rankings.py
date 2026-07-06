#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from racedata.providers.ironman.client import IronmanClient
from racedata.providers.mtec.client import MtecClient
from racedata.providers.usat.client import UsatClient, UsatRateLimitError, UsatRequestError
from racedata.providers.usat.rankings_service import UsatRankingsService
from racedata.providers.usat.rankings_store import UsatRankingsStore

from src.usat_rankings.estimate import load_ironman_finishers, load_mtec_finishers, run_estimate, run_match_report
from src.usat_rankings.report import format_estimate_report, format_match_report
from src.usat_rankings.scrape_progress import ConsoleScrapeReporter

DEFAULT_DB = ROOT / "data" / "usat_rankings.db"
DEFAULT_RACE = "rockford703-2026"


def _default_db_path() -> Path:
    return DEFAULT_DB


def cmd_scrape(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    store = UsatRankingsStore(args.db)
    progress = None if args.quiet else ConsoleScrapeReporter()
    service = UsatRankingsService(client=UsatClient(), store=store, progress=progress)
    try:
        summary = service.scrape_filtered(year=args.year, discipline=args.discipline)
    except (UsatRateLimitError, UsatRequestError) as exc:
        print(f"USAT fetch failed: {exc}", file=sys.stderr)
        print(
            "This is usually transient (timeout, rate limit, or server overload). "
            "Wait 15–30 minutes and rerun the same command; completed periods are cached.",
            file=sys.stderr,
        )
        return 1
    finally:
        store.close()

    if args.quiet:
        print(
            f"Scraped {len(summary.scraped_periods)} period(s), "
            f"{summary.total_athletes} athletes, "
            f"{summary.http_requests} requests, "
            f"{summary.elapsed_seconds:.1f}s."
        )
    return 0


def cmd_match_report(args: argparse.Namespace) -> int:
    store = UsatRankingsStore(args.db)
    try:
        finishers = _load_finishers(args)
        report = run_match_report(
            finishers,
            store,
            pacesetter_year=args.pacesetter_year,
            discipline=args.discipline,
        )
    finally:
        store.close()
    print(format_match_report(report))
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    store = UsatRankingsStore(args.db)
    try:
        finishers = _load_finishers(args)
        report = run_estimate(
            finishers,
            store,
            pacesetter_year=args.pacesetter_year,
            discipline=args.discipline,
        )
    finally:
        store.close()
    print(format_estimate_report(report, limit=args.limit, name_query=args.name))
    return 0


def _load_finishers(args: argparse.Namespace):
    if args.source == "ironman":
        return load_ironman_finishers(args.race, client=IronmanClient())
    if args.source == "mtec":
        return load_mtec_finishers(args.race, client=MtecClient())
    raise SystemExit(f"Unsupported source: {args.source}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Estimate USAT race scores from race results.")
    parser.add_argument(
        "--db",
        type=Path,
        default=_default_db_path(),
        help=f"SQLite rankings cache path (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--discipline",
        default="Triathlon",
        help="USAT discipline for pacesetter lookup (default: Triathlon)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape", help="Scrape USAT ranking period pages into SQLite")
    scrape.add_argument("--year", type=int, required=True)
    scrape.add_argument("--discipline", default="Triathlon")
    scrape.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output (prints one-line summary to stdout)",
    )
    scrape.add_argument(
        "--verbose",
        action="store_true",
        help="Log scrape warnings and save diagnostics to stderr",
    )
    scrape.set_defaults(func=cmd_scrape)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--race", default=DEFAULT_RACE, help=f"Race key (default: {DEFAULT_RACE})")
    shared.add_argument(
        "--source",
        choices=("ironman", "mtec"),
        default="ironman",
        help="Race results source",
    )
    shared.add_argument(
        "--pacesetter-year",
        type=int,
        default=2025,
        help="Prior-year USAT rankings to use for pacesetters",
    )

    match_report = subparsers.add_parser(
        "match-report",
        parents=[shared],
        help="Report pacesetter name-match statistics for a race",
    )
    match_report.set_defaults(func=cmd_match_report)

    estimate = subparsers.add_parser(
        "estimate",
        parents=[shared],
        help="Estimate USAT race scores for a race",
    )
    estimate.add_argument("--limit", type=int, default=25, help="Rows to show in score summary")
    estimate.add_argument(
        "--name",
        help="Show estimated scores for finishers whose name contains this text (case-insensitive)",
    )
    estimate.set_defaults(func=cmd_estimate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
