"""Tests for API key dependency."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.middleware.api_key import require_api_key


def _make_db(result_obj: object | None) -> MagicMock:
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = result_obj
    db.execute = AsyncMock(return_value=execute_result)
    return db


def test_require_api_key_missing_header() -> None:
    db = _make_db(None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(require_api_key(api_key=None, db=db))

    assert exc_info.value.status_code == 401
    db.execute.assert_not_called()


def test_require_api_key_invalid_value() -> None:
    db = _make_db(None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(require_api_key(api_key="invalid-key", db=db))

    assert exc_info.value.status_code == 403


def test_require_api_key_valid_value() -> None:
    key_obj = MagicMock()
    key_obj.key = "valid-key"
    db = _make_db(key_obj)

    result = asyncio.run(require_api_key(api_key="valid-key", db=db))

    assert result is key_obj
