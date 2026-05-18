from __future__ import annotations

from racedata.core.comparison import build_comparison_rows, format_delta
from racedata.core.models import AthleteRef, ComparisonRow, Race, SegmentColumn

_START_SEGMENT_IDS = frozenset({"START"})


def _is_start_segment(segment_id: str, label: str) -> bool:
    if segment_id.upper() in _START_SEGMENT_IDS:
        return True
    return label.strip().lower() == "start"


def _leg_header_label(segment_id: str, segment_label: str) -> str:
    sid = segment_id.upper()
    if sid in {"FINISH", "RUN"} or segment_label.strip().lower() == "finish":
        return "Run"
    return "Leg"


def _filter_start_column(
    columns: list[SegmentColumn], rows: list[ComparisonRow]
) -> tuple[list[SegmentColumn], list[ComparisonRow]]:
    keep_indices = [
        index
        for index, column in enumerate(columns)
        if not _is_start_segment(column.segment_id, column.label)
    ]
    filtered_columns = [columns[index] for index in keep_indices]
    filtered_rows: list[ComparisonRow] = []
    for row in rows:
        filtered_cells = [row.cells[index] for index in keep_indices]
        filtered_rows.append(
            ComparisonRow(
                athlete=row.athlete,
                is_baseline=row.is_baseline,
                cells=filtered_cells,
            )
        )
    return filtered_columns, filtered_rows


def _build_column_groups(columns: list[SegmentColumn]) -> list[dict]:
    return [
        {
            "segment_id": column.segment_id,
            "label": column.label,
            "leg_label": _leg_header_label(column.segment_id, column.label),
        }
        for column in columns
    ]


def _display_cell_from_segment_cell(cell: dict, *, kind: str, is_baseline: bool) -> dict:
    if kind == "clock":
        return {
            "kind": "clock",
            "value": cell["clock_time"],
            "seconds": cell["clock_seconds"],
            "delta": None if is_baseline else cell["clock_delta"],
            "delta_seconds": None if is_baseline else cell["clock_delta_seconds"],
        }
    return {
        "kind": "leg",
        "value": cell["leg_time"],
        "seconds": cell["leg_seconds"],
        "delta": None if is_baseline else cell["leg_delta"],
        "delta_seconds": None if is_baseline else cell["leg_delta_seconds"],
    }


def _expand_display_cells(cells: list[dict], *, is_baseline: bool) -> list[dict]:
    display_cells: list[dict] = []
    for cell in cells:
        display_cells.append(
            _display_cell_from_segment_cell(cell, kind="clock", is_baseline=is_baseline)
        )
        display_cells.append(
            _display_cell_from_segment_cell(cell, kind="leg", is_baseline=is_baseline)
        )
    return display_cells


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
    columns, rows = _filter_start_column(columns, rows)
    column_groups = _build_column_groups(columns)
    row_dicts = [_row_to_dict(row) for row in rows]
    for row_dict in row_dicts:
        row_dict["display_cells"] = _expand_display_cells(
            row_dict["cells"],
            is_baseline=row_dict["is_baseline"],
        )
    return {
        "race": race,
        "race_title": race.display_name,
        "course_label": course_label,
        "available_courses": available_courses or [],
        "selected_course": selected_course,
        "columns": [{"segment_id": c.segment_id, "label": c.label} for c in columns],
        "column_groups": column_groups,
        "rows": row_dicts,
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
