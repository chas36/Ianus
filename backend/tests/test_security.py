"""Tests for role-based access control."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models import User
from app.security import require_role


def _make_user(role: str) -> User:
    user = MagicMock(spec=User)
    user.role = role
    user.username = "testuser"
    user.is_active = True
    return user


def test_require_role_admin_passes() -> None:
    checker = require_role("admin")
    user = _make_user("admin")
    result = checker(user)
    assert result is user


def test_require_role_admin_blocks_teacher() -> None:
    checker = require_role("admin")
    user = _make_user("teacher")
    with pytest.raises(HTTPException) as exc_info:
        checker(user)
    assert exc_info.value.status_code == 403


def test_require_role_teacher_passes() -> None:
    checker = require_role("admin", "teacher")
    user = _make_user("teacher")
    result = checker(user)
    assert result is user


def test_require_role_multiple_roles() -> None:
    checker = require_role("admin", "teacher")
    admin = _make_user("admin")
    teacher = _make_user("teacher")
    assert checker(admin) is admin
    assert checker(teacher) is teacher
