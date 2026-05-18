from __future__ import annotations

from racedata.core.comparison import build_comparison_rows, format_delta
from racedata.core.models import AthleteRef, ComparisonRow, Race, SegmentColumn


def build_grid_view(
    race: Race,
    athletes: list[AthleteRef],
    splits_by_profile: dict[str, list],
    *,
    baseline_index: int = 0,
    course_label: str | None = None,
    available_courses: list[dict] | None = None,
    selected_course: str | None = None,
) -> dict:
    columns, rows = build_comparison_rows(
        athletes,
        splits_by_profile,
        baseline_index=baseline_index,
    )
    return {
        "race": race,
        "race_title": race.display_name,
        "course_label": course_label,
        "available_courses": available_courses or [],
        "selected_course": selected_course,
        "columns": columns,
        "rows": [_row_to_dict(row) for row in rows],
        "baseline_index": baseline_index,
    }


def _row_to_dict(row: ComparisonRow) -> dict:
    return {
        "athlete": {
            "profile_id": row.athlete.profile_id,
            "entry_id": row.athlete.entry_id,
            "name": row.athlete.name,
            "bib": row.athlete.bib,
            "division": row.athlete.division,
        },
        "is_baseline": row.is_baseline,
        "cells": [
            {
                "clock_time": cell.clock_time,
                "leg_time": cell.leg_time,
                "clock_seconds": cell.clock_seconds,
                "leg_seconds": cell.leg_seconds,
                "clock_delta": format_delta(cell.clock_delta_seconds),
                "leg_delta": format_delta(cell.leg_delta_seconds),
                "clock_delta_seconds": cell.clock_delta_seconds,
                "leg_delta_seconds": cell.leg_delta_seconds,
            }
            for cell in row.cells
        ],
    }


def column_labels(columns: list[SegmentColumn]) -> list[str]:
    return [column.label for column in columns]
