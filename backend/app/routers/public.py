"""Public API — no authentication required.

Read-only endpoints for timetable data. Used by Telegram bots and
external systems (e.g. school's unified backend).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.api_key import require_api_key
from app.models import ApiKey, Card, Room, RoomBooking, SchoolClass, Teacher
from app.routers.timetable import (
    PERIOD_TIMES,
    timetable_by_class,
    timetable_by_room,
    timetable_by_teacher,
)
from app.schemas import (
    ClassOut,
    RoomBookingCreateRequest,
    RoomBookingOut,
    RoomOut,
    TeacherOut,
    TimetableResponse,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/public", tags=["public"])

MSK = timezone(timedelta(hours=3))

DAY_NAMES = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
}

PERIOD_RANGES: list[tuple[str, str]] = [
    ("08:30", "09:15"),
    ("09:30", "10:15"),
    ("10:30", "11:15"),
    ("11:30", "12:15"),
    ("12:25", "13:10"),
    ("13:30", "14:15"),
    ("14:35", "15:20"),
    ("15:30", "16:15"),
    ("16:25", "17:10"),
    ("17:20", "18:05"),
]


def _time_to_minutes(t: str) -> int:
    hours, minutes = t.split(":")
    return int(hours) * 60 + int(minutes)


def _get_current_period(time_str: str) -> int:
    """Return current period number (1-10) or 0 if outside school hours."""
    now_minutes = _time_to_minutes(time_str)
    for index, (start, end) in enumerate(PERIOD_RANGES, 1):
        if _time_to_minutes(start) <= now_minutes <= _time_to_minutes(end):
            return index
    return 0


def _get_today_weekday() -> int:
    """Return 1=Mon, 2=Tue, ..., 5=Fri, 0=weekend."""
    now = datetime.now(MSK)
    weekday = now.isoweekday()
    return weekday if weekday <= 5 else 0


def _filter_timetable_by_day(tt: TimetableResponse, day: int) -> list[dict[str, Any]]:
    """Extract lessons for a specific day as flat list."""
    result: list[dict[str, Any]] = []
    for row in tt.rows:
        cells = row.days.get(day, [])
        for cell in cells:
            result.append(
                {
                    "period": row.period,
                    "time": row.time,
                    "subject": cell.subject,
                    "teacher": cell.teacher,
                    "room": cell.room,
                    "group": cell.group,
                }
            )
    return result


def _find_free_rooms_from_timetables(
    all_rooms: list[dict[str, Any]],
    busy_room_ids: set[int],
) -> list[dict[str, Any]]:
    return [room for room in all_rooms if room["id"] not in busy_room_ids]


def _weekday_for_date(value: date) -> int:
    weekday = value.isoweekday()
    return weekday if weekday <= 5 else 0


def _resolve_day_query(day: int, booking_date: date | None) -> int:
    if booking_date is not None:
        date_day = _weekday_for_date(booking_date)
        if date_day == 0:
            return 0
        if day not in (0, date_day):
            raise HTTPException(status_code=400, detail="day does not match date")
        return date_day

    if day == 0:
        return _get_today_weekday()
    return day


@router.get("/classes", response_model=list[ClassOut])
async def public_list_classes(db: AsyncSession = Depends(get_db)) -> list[SchoolClass]:
    result = await db.execute(select(SchoolClass).order_by(SchoolClass.name))
    return list(result.scalars().all())


@router.get("/teachers", response_model=list[TeacherOut])
async def public_list_teachers(db: AsyncSession = Depends(get_db)) -> list[Teacher]:
    result = await db.execute(select(Teacher).order_by(Teacher.name))
    return list(result.scalars().all())


@router.get("/rooms", response_model=list[RoomOut])
async def public_list_rooms(db: AsyncSession = Depends(get_db)) -> list[Room]:
    result = await db.execute(select(Room).order_by(Room.name))
    return list(result.scalars().all())


@router.get("/timetable/class/{class_id}")
async def public_class_timetable(
    class_id: int,
    day: int = Query(default=0, ge=0, le=5, description="1=Пн..5=Пт, 0=сегодня"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "day_name": "выходной", "lessons": []}

    tt = await timetable_by_class(class_id, db)
    return {
        "day": day,
        "day_name": DAY_NAMES[day],
        "entity": tt.entity_name,
        "lessons": _filter_timetable_by_day(tt, day),
    }


@router.get("/timetable/teacher/{teacher_id}")
async def public_teacher_timetable(
    teacher_id: int,
    day: int = Query(default=0, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "day_name": "выходной", "lessons": []}

    tt = await timetable_by_teacher(teacher_id, db)
    return {
        "day": day,
        "day_name": DAY_NAMES[day],
        "entity": tt.entity_name,
        "lessons": _filter_timetable_by_day(tt, day),
    }


@router.get("/timetable/room/{room_id}")
async def public_room_timetable(
    room_id: int,
    day: int = Query(default=0, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "day_name": "выходной", "lessons": []}

    tt = await timetable_by_room(room_id, db)
    return {
        "day": day,
        "day_name": DAY_NAMES[day],
        "entity": tt.entity_name,
        "lessons": _filter_timetable_by_day(tt, day),
    }


@router.get("/teacher/{teacher_id}/now")
async def public_teacher_now(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    day = _get_today_weekday()
    if day == 0:
        return {"status": "weekend", "message": "Сегодня выходной"}

    now = datetime.now(MSK)
    period = _get_current_period(now.strftime("%H:%M"))

    tt = await timetable_by_teacher(teacher_id, db)

    if period == 0:
        return {
            "status": "no_lesson",
            "message": "Сейчас нет уроков",
            "teacher": tt.entity_name,
        }

    lessons = tt.rows[period - 1].days.get(day, [])
    if not lessons:
        return {
            "status": "free",
            "message": f"Урок {period} — нет занятий",
            "teacher": tt.entity_name,
            "period": period,
            "time": PERIOD_TIMES.get(period, ""),
        }

    lesson = lessons[0]
    return {
        "status": "teaching",
        "teacher": tt.entity_name,
        "period": period,
        "time": PERIOD_TIMES.get(period, ""),
        "subject": lesson.subject,
        "class": lesson.teacher,
        "room": lesson.room,
    }


@router.get("/rooms/free")
async def public_free_rooms(
    day: int = Query(default=0, ge=0, le=5, description="1=Пн..5=Пт, 0=сегодня"),
    period: int = Query(default=0, ge=0, le=10, description="1-10, 0=текущий"),
    booking_date: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.now(MSK)
    requested_day = day
    day = _resolve_day_query(day, booking_date)
    target_date = booking_date or (now.date() if requested_day == 0 else None)

    if day == 0:
        return {"day": 0, "message": "Сегодня выходной", "free_rooms": []}

    if period == 0:
        if target_date is not None and target_date != now.date():
            raise HTTPException(
                status_code=400,
                detail="period=0 is supported only for current date",
            )
        period = _get_current_period(now.strftime("%H:%M"))
        if period == 0:
            return {
                "day": day,
                "period": 0,
                "message": "Сейчас нет уроков",
                "free_rooms": [],
            }

    all_rooms_result = await db.execute(select(Room).order_by(Room.name))
    all_rooms = [{"id": room.id, "name": room.name} for room in all_rooms_result.scalars().all()]

    busy_result = await db.execute(
        select(Card.room_id).where(
            Card.day == day,
            Card.period == period,
            Card.room_id.is_not(None),
        )
    )
    busy_room_ids = {row[0] for row in busy_result.all()}
    booked_room_ids: set[int] = set()

    if target_date is not None:
        booked_result = await db.execute(
            select(RoomBooking.room_id).where(
                RoomBooking.day == day,
                RoomBooking.period == period,
                RoomBooking.date == target_date,
            )
        )
        booked_room_ids = {row[0] for row in booked_result.all()}
        busy_room_ids |= booked_room_ids

    free_rooms = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)

    return {
        "day": day,
        "day_name": DAY_NAMES[day],
        "period": period,
        "time": PERIOD_TIMES.get(period, ""),
        "date": target_date.isoformat() if target_date else None,
        "free_rooms": free_rooms,
        "total_rooms": len(all_rooms),
        "busy_rooms": len(busy_room_ids),
        "booked_rooms": len(booked_room_ids),
    }


@router.post(
    "/rooms/{room_id}/book",
    response_model=RoomBookingOut,
    status_code=status.HTTP_201_CREATED,
)
async def public_book_room(
    room_id: int,
    payload: RoomBookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key),
) -> RoomBooking:
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if payload.date.isoweekday() != payload.day:
        raise HTTPException(status_code=400, detail="day does not match date")

    card_exists = await db.scalar(
        select(Card.id)
        .where(
            Card.room_id == room_id,
            Card.day == payload.day,
            Card.period == payload.period,
        )
        .limit(1)
    )
    if card_exists is not None:
        raise HTTPException(status_code=409, detail="Room is busy in timetable")

    booking_exists = await db.scalar(
        select(RoomBooking.id)
        .where(
            RoomBooking.room_id == room_id,
            RoomBooking.day == payload.day,
            RoomBooking.period == payload.period,
            RoomBooking.date == payload.date,
        )
        .limit(1)
    )
    if booking_exists is not None:
        raise HTTPException(status_code=409, detail="Room is already booked")

    booking = RoomBooking(
        room_id=room_id,
        day=payload.day,
        period=payload.period,
        date=payload.date,
        booked_by=payload.booked_by.strip(),
        purpose=payload.purpose.strip() if payload.purpose else None,
    )
    db.add(booking)
    await db.flush()

    await log_action(
        db,
        "book_room",
        detail=(
            f"API key {api_key.name} booked room {room.name} "
            f"for {payload.date.isoformat()} period {payload.period}"
        ),
    )
    await db.commit()
    await db.refresh(booking)
    return booking


@router.delete(
    "/rooms/{room_id}/book/{booking_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def public_cancel_room_booking(
    room_id: int,
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key),
) -> Response:
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    booking = await db.get(RoomBooking, booking_id)
    if booking is None or booking.room_id != room_id:
        raise HTTPException(status_code=404, detail="Booking not found")

    await db.delete(booking)
    await log_action(
        db,
        "cancel_room_booking",
        detail=(
            f"API key {api_key.name} canceled booking {booking.id} "
            f"for room {room.name}"
        ),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
