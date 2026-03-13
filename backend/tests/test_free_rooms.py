"""Tests for free rooms logic."""

from app.routers.public import _find_free_rooms_from_timetables


def test_find_free_rooms_basic() -> None:
    all_rooms = [{"id": 1, "name": "301"}, {"id": 2, "name": "302"}]
    busy_room_ids = {1}

    result = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)
    assert len(result) == 1
    assert result[0]["id"] == 2
    assert result[0]["name"] == "302"


def test_all_rooms_busy() -> None:
    all_rooms = [{"id": 1, "name": "301"}]
    busy_room_ids = {1}

    result = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)
    assert result == []


def test_all_rooms_free() -> None:
    all_rooms = [{"id": 1, "name": "301"}, {"id": 2, "name": "302"}]
    busy_room_ids: set[int] = set()

    result = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)
    assert len(result) == 2
