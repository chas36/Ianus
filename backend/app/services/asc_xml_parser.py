"""Parser for aSc Timetables XML export format."""

from __future__ import annotations

from xml.etree import ElementTree as ET

DAY_BITS = {
    "10000": 1,
    "01000": 2,
    "00100": 3,
    "00010": 4,
    "00001": 5,
}


def _parse_day(days_str: str) -> int:
    if days_str in DAY_BITS:
        return DAY_BITS[days_str]
    if len(days_str) == 5:
        for idx, bit in enumerate(days_str, start=1):
            if bit == "1":
                return idx
    return 0


def parse_asc_xml(xml_bytes: bytes) -> dict[str, list[dict[str, object]]]:
    try:
        text = xml_bytes.decode("windows-1251")
    except UnicodeDecodeError:
        text = xml_bytes.decode("utf-8")

    root = ET.fromstring(text)

    groups_by_id: dict[str, dict[str, object]] = {}
    for group in root.findall(".//group"):
        gid = group.get("id")
        if gid:
            groups_by_id[gid] = {
                "name": group.get("name", ""),
                "entireclass": group.get("entireclass") == "1",
            }

    subjects = [
        {
            "asc_id": subject.get("id"),
            "name": subject.get("name", ""),
            "short_name": subject.get("short", ""),
        }
        for subject in root.findall(".//subject")
    ]

    teachers = [
        {
            "asc_id": teacher.get("id"),
            "name": teacher.get("name", ""),
            "short_name": teacher.get("short", ""),
            "color": teacher.get("color"),
        }
        for teacher in root.findall(".//teacher")
    ]

    classes = [
        {
            "asc_id": school_class.get("id"),
            "name": school_class.get("name", ""),
            "short_name": school_class.get("short", ""),
        }
        for school_class in root.findall(".//class")
    ]

    rooms = [
        {
            "asc_id": room.get("id"),
            "name": room.get("name", ""),
            "short_name": room.get("short", ""),
        }
        for room in root.findall(".//classroom")
    ]

    lessons: list[dict[str, object]] = []
    for lesson in root.findall(".//lesson"):
        teacher_ids = lesson.get("teacherids", "").split(",")
        class_ids = lesson.get("classids", "").split(",")
        group_ids = lesson.get("groupids", "").split(",")

        group_name = None
        for group_id in group_ids:
            group_id = group_id.strip()
            group = groups_by_id.get(group_id)
            if not group:
                continue
            if not group["entireclass"]:
                group_name = str(group["name"])
                break

        lessons.append(
            {
                "asc_id": lesson.get("id"),
                "subject_asc_id": lesson.get("subjectid", ""),
                "teacher_asc_id": teacher_ids[0].strip() if teacher_ids and teacher_ids[0].strip() else None,
                "class_asc_id": class_ids[0].strip() if class_ids and class_ids[0].strip() else None,
                "group_name": group_name,
                "periods_per_week": float(lesson.get("periodsperweek", "1.0")),
            }
        )

    cards: list[dict[str, object]] = []
    for card in root.findall(".//card"):
        room_ids = card.get("classroomids", "").split(",")
        cards.append(
            {
                "lesson_asc_id": card.get("lessonid", ""),
                "room_asc_id": room_ids[0].strip() if room_ids and room_ids[0].strip() else None,
                "day": _parse_day(card.get("days", "")),
                "period": int(card.get("period", "0")),
            }
        )

    return {
        "subjects": subjects,
        "teachers": teachers,
        "classes": classes,
        "rooms": rooms,
        "lessons": lessons,
        "cards": cards,
    }
