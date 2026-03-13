from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Card, Import, Lesson, Room, SchoolClass, Subject, Teacher, User
from app.schemas import ImportResponse
from app.security import get_current_user, require_role
from app.services.audit import log_action
from app.services.asc_xml_parser import parse_asc_xml

router = APIRouter(
    prefix="/api/import",
    tags=["import"],
    dependencies=[Depends(require_role("admin"))],
)


@router.post("/asc-xml", response_model=ImportResponse)
async def import_asc_xml(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResponse:
    xml_bytes = await file.read()
    data = parse_asc_xml(xml_bytes)

    subject_map: dict[str, int] = {}
    for subject in data["subjects"]:
        asc_id = str(subject["asc_id"])
        existing = (
            await db.execute(select(Subject).where(Subject.asc_id == asc_id))
        ).scalar_one_or_none()

        if existing:
            existing.name = str(subject["name"])
            existing.short_name = str(subject["short_name"])
            obj = existing
        else:
            obj = Subject(
                asc_id=asc_id,
                name=str(subject["name"]),
                short_name=str(subject["short_name"]),
            )
            db.add(obj)

        await db.flush()
        subject_map[asc_id] = obj.id

    teacher_map: dict[str, int] = {}
    for teacher in data["teachers"]:
        asc_id = str(teacher["asc_id"])
        existing = (
            await db.execute(select(Teacher).where(Teacher.asc_id == asc_id))
        ).scalar_one_or_none()

        if existing:
            existing.name = str(teacher["name"])
            existing.short_name = str(teacher["short_name"])
            existing.color = str(teacher["color"]) if teacher["color"] is not None else None
            obj = existing
        else:
            obj = Teacher(
                asc_id=asc_id,
                name=str(teacher["name"]),
                short_name=str(teacher["short_name"]),
                color=str(teacher["color"]) if teacher["color"] is not None else None,
            )
            db.add(obj)

        await db.flush()
        teacher_map[asc_id] = obj.id

    class_map: dict[str, int] = {}
    for school_class in data["classes"]:
        asc_id = str(school_class["asc_id"])
        existing = (
            await db.execute(select(SchoolClass).where(SchoolClass.asc_id == asc_id))
        ).scalar_one_or_none()

        if existing:
            existing.name = str(school_class["name"])
            existing.short_name = str(school_class["short_name"])
            obj = existing
        else:
            obj = SchoolClass(
                asc_id=asc_id,
                name=str(school_class["name"]),
                short_name=str(school_class["short_name"]),
            )
            db.add(obj)

        await db.flush()
        class_map[asc_id] = obj.id

    room_map: dict[str, int] = {}
    for room in data["rooms"]:
        asc_id = str(room["asc_id"])
        existing = (
            await db.execute(select(Room).where(Room.asc_id == asc_id))
        ).scalar_one_or_none()

        if existing:
            existing.name = str(room["name"])
            existing.short_name = str(room["short_name"])
            obj = existing
        else:
            obj = Room(
                asc_id=asc_id,
                name=str(room["name"]),
                short_name=str(room["short_name"]),
            )
            db.add(obj)

        await db.flush()
        room_map[asc_id] = obj.id

    lesson_map: dict[str, int] = {}
    for lesson in data["lessons"]:
        lesson_asc_id = str(lesson["asc_id"])
        subject_id = subject_map.get(str(lesson["subject_asc_id"]))
        class_id = class_map.get(str(lesson["class_asc_id"]))
        teacher_asc_id = lesson["teacher_asc_id"]
        teacher_id = teacher_map.get(str(teacher_asc_id)) if teacher_asc_id else None

        if not subject_id or not class_id:
            continue

        existing = (
            await db.execute(select(Lesson).where(Lesson.asc_id == lesson_asc_id))
        ).scalar_one_or_none()

        if existing:
            existing.subject_id = subject_id
            existing.teacher_id = teacher_id
            existing.class_id = class_id
            existing.group_name = str(lesson["group_name"]) if lesson["group_name"] is not None else None
            existing.periods_per_week = float(lesson["periods_per_week"])
            obj = existing
        else:
            obj = Lesson(
                asc_id=lesson_asc_id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                class_id=class_id,
                group_name=str(lesson["group_name"]) if lesson["group_name"] is not None else None,
                periods_per_week=float(lesson["periods_per_week"]),
            )
            db.add(obj)

        await db.flush()
        lesson_map[lesson_asc_id] = obj.id

    await db.execute(delete(Card))
    cards_count = 0
    for card in data["cards"]:
        lesson_id = lesson_map.get(str(card["lesson_asc_id"]))
        if not lesson_id:
            continue

        day = int(card["day"])
        if day == 0:
            continue

        room_asc_id = card["room_asc_id"]
        room_id = room_map.get(str(room_asc_id)) if room_asc_id else None

        db.add(
            Card(
                lesson_id=lesson_id,
                room_id=room_id,
                day=day,
                period=int(card["period"]),
            )
        )
        cards_count += 1

    db.add(Import(filename=file.filename or "unknown", source_format="asc-xml"))
    await log_action(
        db,
        "import",
        detail=f"Imported {file.filename}: {len(data['subjects'])} subjects, {cards_count} cards",
        user=current_user,
    )
    await db.commit()

    return ImportResponse(
        subjects=len(data["subjects"]),
        teachers=len(data["teachers"]),
        classes=len(data["classes"]),
        rooms=len(data["rooms"]),
        lessons=len(data["lessons"]),
        cards=cards_count,
    )
