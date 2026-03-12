from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Card, Lesson, Room, SchoolClass, Teacher
from app.schemas import (
    ClassOut,
    RoomOut,
    TeacherOut,
    TimetableCell,
    TimetableResponse,
    TimetableRow,
)

router = APIRouter(prefix="/api", tags=["timetable"])

PERIOD_TIMES = {
    1: "8:30 - 9:15",
    2: "9:30 - 10:15",
    3: "10:30 - 11:15",
    4: "11:30 - 12:15",
    5: "12:25 - 13:10",
    6: "13:30 - 14:15",
    7: "14:35 - 15:20",
    8: "15:30 - 16:15",
    9: "16:25 - 17:10",
    10: "17:20 - 18:05",
}


@router.get("/classes", response_model=list[ClassOut])
async def list_classes(db: AsyncSession = Depends(get_db)) -> list[SchoolClass]:
    result = await db.execute(select(SchoolClass).order_by(SchoolClass.name))
    return list(result.scalars().all())


@router.get("/teachers", response_model=list[TeacherOut])
async def list_teachers(db: AsyncSession = Depends(get_db)) -> list[Teacher]:
    result = await db.execute(select(Teacher).order_by(Teacher.name))
    return list(result.scalars().all())


@router.get("/rooms", response_model=list[RoomOut])
async def list_rooms(db: AsyncSession = Depends(get_db)) -> list[Room]:
    result = await db.execute(select(Room).order_by(Room.name))
    return list(result.scalars().all())


async def _build_timetable(
    cards_query: Any,
    entity_type: str,
    entity_name: str,
    db: AsyncSession,
    cell_builder: Callable[[Card, Lesson], TimetableCell],
) -> TimetableResponse:
    result = await db.execute(cards_query)
    cards = result.unique().scalars().all()

    grid: dict[int, dict[int, list[TimetableCell]]] = {}
    for card in cards:
        lesson = card.lesson
        cell = cell_builder(card, lesson)
        grid.setdefault(card.period, {}).setdefault(card.day, []).append(cell)

    rows: list[TimetableRow] = []
    for period in range(1, 11):
        days_data = {day: grid.get(period, {}).get(day, []) for day in range(1, 6)}
        rows.append(
            TimetableRow(
                period=period,
                time=PERIOD_TIMES.get(period, ""),
                days=days_data,
            )
        )

    return TimetableResponse(entity_type=entity_type, entity_name=entity_name, rows=rows)


@router.get("/timetable/class/{class_id}", response_model=TimetableResponse)
async def timetable_by_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
) -> TimetableResponse:
    school_class = await db.get(SchoolClass, class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    query = (
        select(Card)
        .join(Card.lesson)
        .where(Lesson.class_id == class_id)
        .options(
            selectinload(Card.lesson).selectinload(Lesson.subject),
            selectinload(Card.lesson).selectinload(Lesson.teacher),
            selectinload(Card.room),
        )
    )

    def build_cell(card: Card, lesson: Lesson) -> TimetableCell:
        return TimetableCell(
            subject=lesson.subject.name,
            teacher=lesson.teacher.name if lesson.teacher else None,
            room=card.room.name if card.room else None,
            group=lesson.group_name,
        )

    return await _build_timetable(query, "class", school_class.name, db, build_cell)


@router.get("/timetable/teacher/{teacher_id}", response_model=TimetableResponse)
async def timetable_by_teacher(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
) -> TimetableResponse:
    teacher = await db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    query = (
        select(Card)
        .join(Card.lesson)
        .where(Lesson.teacher_id == teacher_id)
        .options(
            selectinload(Card.lesson).selectinload(Lesson.subject),
            selectinload(Card.lesson).selectinload(Lesson.school_class),
            selectinload(Card.room),
        )
    )

    def build_cell(card: Card, lesson: Lesson) -> TimetableCell:
        return TimetableCell(
            subject=lesson.subject.name,
            teacher=lesson.school_class.name,
            room=card.room.name if card.room else None,
            group=lesson.group_name,
        )

    return await _build_timetable(query, "teacher", teacher.name, db, build_cell)


@router.get("/timetable/room/{room_id}", response_model=TimetableResponse)
async def timetable_by_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
) -> TimetableResponse:
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    query = (
        select(Card)
        .where(Card.room_id == room_id)
        .options(
            selectinload(Card.lesson).selectinload(Lesson.subject),
            selectinload(Card.lesson).selectinload(Lesson.school_class),
            selectinload(Card.lesson).selectinload(Lesson.teacher),
        )
    )

    def build_cell(card: Card, lesson: Lesson) -> TimetableCell:
        return TimetableCell(
            subject=lesson.subject.name,
            teacher=lesson.school_class.name,
            room=lesson.teacher.short_name if lesson.teacher else None,
            group=lesson.group_name,
        )

    return await _build_timetable(query, "room", room.name, db, build_cell)
