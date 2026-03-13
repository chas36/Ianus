"""Tests for public API helper endpoints (no auth required)."""

from app.schemas import TimetableCell, TimetableResponse, TimetableRow

from app.routers.public import _filter_timetable_by_day, _get_current_period


def test_day_filter_extracts_correct_cells() -> None:
    row = TimetableRow(
        period=1,
        time="8:30 - 9:15",
        days={
            1: [TimetableCell(subject="Математика", teacher="Иванов", room="301", group=None)],
            2: [TimetableCell(subject="Физика", teacher="Петров", room="302", group=None)],
            3: [],
            4: [],
            5: [],
        },
    )
    tt = TimetableResponse(entity_type="class", entity_name="9А", rows=[row])

    result = _filter_timetable_by_day(tt, 1)
    assert len(result) == 1
    assert result[0]["period"] == 1
    assert result[0]["subject"] == "Математика"
    assert result[0]["teacher"] == "Иванов"
    assert result[0]["room"] == "301"


def test_day_filter_skips_empty_periods() -> None:
    rows = [
        TimetableRow(period=1, time="8:30", days={1: [], 2: [], 3: [], 4: [], 5: []}),
        TimetableRow(
            period=2,
            time="9:30",
            days={
                1: [TimetableCell(subject="Химия", teacher="Сидоров", room="216", group=None)],
                2: [],
                3: [],
                4: [],
                5: [],
            },
        ),
    ]
    tt = TimetableResponse(entity_type="class", entity_name="9А", rows=rows)

    result = _filter_timetable_by_day(tt, 1)
    assert len(result) == 1
    assert result[0]["period"] == 2


def test_current_period_detection() -> None:
    assert _get_current_period("10:35") == 3
    assert _get_current_period("08:00") == 0
    assert _get_current_period("18:30") == 0
    assert _get_current_period("09:30") == 2
