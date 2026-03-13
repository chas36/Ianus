"""Tests for public API day/date resolution."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.routers.public import _resolve_day_query, _weekday_for_date


def test_weekday_for_date_handles_weekdays_and_weekend() -> None:
    assert _weekday_for_date(date(2026, 3, 13)) == 5
    assert _weekday_for_date(date(2026, 3, 14)) == 0


def test_resolve_day_query_uses_date_when_provided() -> None:
    result = _resolve_day_query(0, date(2026, 3, 12))
    assert result == 4


def test_resolve_day_query_rejects_mismatch() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _resolve_day_query(2, date(2026, 3, 13))
    assert exc_info.value.status_code == 400
