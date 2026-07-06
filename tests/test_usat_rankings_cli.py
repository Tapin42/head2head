
def test_cli_parser_has_commands():
    from scripts.usat_rankings import build_parser

    parser = build_parser()
    args = parser.parse_args(["scrape", "--year", "2025"])
    assert args.command == "scrape"
    assert args.year == 2025

    args = parser.parse_args(["estimate", "--race", "rockford703-2026"])
    assert args.command == "estimate"
    assert args.race == "rockford703-2026"

    args = parser.parse_args(["estimate", "--race", "door-county-sprint-2025", "--source", "mtec"])
    assert args.source == "mtec"
    assert args.race == "door-county-sprint-2025"
