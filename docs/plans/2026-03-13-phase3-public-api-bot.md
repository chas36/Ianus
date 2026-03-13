# Phase 3: Public API + Telegram Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Public read API for timetable data (no auth), API-key-protected room booking, and a reference Telegram bot (aiogram 3) that teachers and students use to check schedules, find teachers, and book rooms.

**Architecture:** New `/api/public/` router with no JWT (read-only). API-key middleware for write operations (booking). Telegram bot as a separate process in `backend/bot/`, communicating with Ianus via its own public API. Bot stores Telegram ID → teacher/class mapping in `bot_users` table.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, aiogram 3.x, PostgreSQL. Bot uses `aiohttp` (bundled with aiogram) to call Ianus API.

**Depends on:** Phase 2 completion (audit logging used for booking events).

## Execution Status (Updated: 2026-03-13)

- [x] Task 1: Public timetable API (lists + by-day endpoints + teacher-now)
- [x] Task 2: Free rooms endpoint (`/api/public/rooms/free`)
- [ ] Task 3: API key model + middleware
- [ ] Task 4: Room booking model + endpoints
- [ ] Task 5: API keys admin endpoints
- [ ] Task 6: Bot skeleton (aiogram 3)
- [ ] Task 7: Bot registration flow
- [ ] Task 8: Bot schedule commands
- [ ] Task 9: Bot teacher lookup
- [ ] Task 10: Bot free rooms + booking
- [ ] Task 11: Public API docs polish

---

## Task 1: Public timetable API — lists

**Files:**
- Create: `backend/app/routers/public.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_public_api.py`

**Step 1: Write the test**

```python
"""Tests for public API endpoints (no auth required)."""
import pytest
from app.services.asc_xml_parser import parse_asc_xml

# We test the parser output shape; integration tests with DB come later.
# Here we test the public router logic in isolation.


def test_day_filter_extracts_correct_cells():
    """Given a full timetable response, filtering by day=1 returns only Monday."""
    from app.routers.public import _filter_timetable_by_day
    from app.schemas import TimetableCell, TimetableResponse, TimetableRow

    row = TimetableRow(
        period=1,
        time="8:30 - 9:15",
        days={
            1: [TimetableCell(subject="Математика", teacher="Иванов", room="301", group=None)],
            2: [TimetableCell(subject="Физика", teacher="Петров", room="302", group=None)],
            3: [], 4: [], 5: [],
        },
    )
    tt = TimetableResponse(entity_type="class", entity_name="9А", rows=[row])

    result = _filter_timetable_by_day(tt, 1)
    assert len(result) == 1
    assert result[0]["period"] == 1
    assert result[0]["subject"] == "Математика"
    assert result[0]["teacher"] == "Иванов"
    assert result[0]["room"] == "301"


def test_day_filter_skips_empty_periods():
    from app.routers.public import _filter_timetable_by_day
    from app.schemas import TimetableCell, TimetableResponse, TimetableRow

    rows = [
        TimetableRow(period=1, time="8:30", days={1: [], 2: [], 3: [], 4: [], 5: []}),
        TimetableRow(
            period=2, time="9:30",
            days={1: [TimetableCell(subject="Химия", teacher="Сидоров", room="216", group=None)],
                  2: [], 3: [], 4: [], 5: []},
        ),
    ]
    tt = TimetableResponse(entity_type="class", entity_name="9А", rows=rows)

    result = _filter_timetable_by_day(tt, 1)
    assert len(result) == 1
    assert result[0]["period"] == 2


def test_current_period_detection():
    from app.routers.public import _get_current_period

    # 10:35 is during period 3 (10:30 - 11:15)
    assert _get_current_period("10:35") == 3
    # 8:00 is before school
    assert _get_current_period("08:00") == 0
    # 18:30 is after school
    assert _get_current_period("18:30") == 0
    # 9:30 is start of period 2
    assert _get_current_period("09:30") == 2
```

**Step 2: Run tests — expect FAIL**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_public_api.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.routers.public'`

**Step 3: Implement public router**

```python
"""Public API — no authentication required.

Read-only endpoints for timetable data. Used by Telegram bots and
external systems (e.g. school's unified backend).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SchoolClass, Teacher, Room
from app.routers.timetable import (
    timetable_by_class,
    timetable_by_teacher,
    timetable_by_room,
    PERIOD_TIMES,
)
from app.schemas import ClassOut, TeacherOut, RoomOut, TimetableResponse

router = APIRouter(prefix="/api/public", tags=["public"])

# Moscow timezone offset
MSK = timezone(timedelta(hours=3))

# Period start/end times for current-period detection
PERIOD_RANGES: list[tuple[str, str]] = [
    ("08:30", "09:15"),  # 1
    ("09:30", "10:15"),  # 2
    ("10:30", "11:15"),  # 3
    ("11:30", "12:15"),  # 4
    ("12:25", "13:10"),  # 5
    ("13:30", "14:15"),  # 6
    ("14:35", "15:20"),  # 7
    ("15:30", "16:15"),  # 8
    ("16:25", "17:10"),  # 9
    ("17:20", "18:05"),  # 10
]


def _time_to_minutes(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _get_current_period(time_str: str) -> int:
    """Return current period number (1-10) or 0 if outside school hours."""
    now_min = _time_to_minutes(time_str)
    for i, (start, end) in enumerate(PERIOD_RANGES, 1):
        if _time_to_minutes(start) <= now_min <= _time_to_minutes(end):
            return i
    return 0


def _get_today_weekday() -> int:
    """Return 1=Mon, 2=Tue, ..., 5=Fri, 0=weekend."""
    now = datetime.now(MSK)
    wd = now.isoweekday()  # 1=Mon, 7=Sun
    return wd if wd <= 5 else 0


def _filter_timetable_by_day(tt: TimetableResponse, day: int) -> list[dict[str, Any]]:
    """Extract lessons for a specific day as flat list."""
    result = []
    for row in tt.rows:
        cells = row.days.get(day, [])
        for cell in cells:
            result.append({
                "period": row.period,
                "time": row.time,
                "subject": cell.subject,
                "teacher": cell.teacher,
                "room": cell.room,
                "group": cell.group,
            })
    return result


# --- List endpoints ---

@router.get("/classes", response_model=list[ClassOut])
async def public_list_classes(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(SchoolClass).order_by(SchoolClass.name))
    return list(result.scalars().all())


@router.get("/teachers", response_model=list[TeacherOut])
async def public_list_teachers(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Teacher).order_by(Teacher.name))
    return list(result.scalars().all())


@router.get("/rooms", response_model=list[RoomOut])
async def public_list_rooms(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Room).order_by(Room.name))
    return list(result.scalars().all())


# --- Timetable by day ---

@router.get("/timetable/class/{class_id}")
async def public_class_timetable(
    class_id: int,
    day: int = Query(default=0, ge=0, le=5, description="1=Пн..5=Пт, 0=сегодня"),
    db: AsyncSession = Depends(get_db),
):
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "day_name": "выходной", "lessons": []}

    tt = await timetable_by_class(class_id, db)
    return {
        "day": day,
        "day_name": ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница"][day],
        "entity": tt.entity_name,
        "lessons": _filter_timetable_by_day(tt, day),
    }


@router.get("/timetable/teacher/{teacher_id}")
async def public_teacher_timetable(
    teacher_id: int,
    day: int = Query(default=0, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
):
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "day_name": "выходной", "lessons": []}

    tt = await timetable_by_teacher(teacher_id, db)
    return {
        "day": day,
        "day_name": ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница"][day],
        "entity": tt.entity_name,
        "lessons": _filter_timetable_by_day(tt, day),
    }


@router.get("/timetable/room/{room_id}")
async def public_room_timetable(
    room_id: int,
    day: int = Query(default=0, ge=0, le=5),
    db: AsyncSession = Depends(get_db),
):
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "day_name": "выходной", "lessons": []}

    tt = await timetable_by_room(room_id, db)
    return {
        "day": day,
        "day_name": ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница"][day],
        "entity": tt.entity_name,
        "lessons": _filter_timetable_by_day(tt, day),
    }


# --- Where is teacher now ---

@router.get("/teacher/{teacher_id}/now")
async def public_teacher_now(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
):
    day = _get_today_weekday()
    if day == 0:
        return {"status": "weekend", "message": "Сегодня выходной"}

    now = datetime.now(MSK)
    time_str = now.strftime("%H:%M")
    period = _get_current_period(time_str)

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
        "class": lesson.teacher,  # in teacher view, 'teacher' field holds class name
        "room": lesson.room,
    }
```

**Step 4: Register in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import public
app.include_router(public.router)
```

**Step 5: Run tests — expect PASS**

```bash
pytest tests/test_public_api.py -v
```

**Step 6: Commit**

```bash
cd ..
git add backend/app/routers/public.py backend/app/main.py backend/tests/test_public_api.py
git commit -m "feat: add public timetable API (no auth, read-only)"
```

---

## Task 2: Free rooms endpoint

**Files:**
- Modify: `backend/app/routers/public.py`
- Create: `backend/tests/test_free_rooms.py`

**Step 1: Write the test**

```python
"""Tests for free rooms logic."""
from app.routers.public import _find_free_rooms_from_timetables


def test_find_free_rooms_basic():
    # Room 1 is busy period 1 day 1, Room 2 is free
    all_rooms = [
        {"id": 1, "name": "301"},
        {"id": 2, "name": "302"},
    ]
    busy_room_ids = {1}  # room 1 is busy

    result = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)
    assert len(result) == 1
    assert result[0]["id"] == 2
    assert result[0]["name"] == "302"


def test_all_rooms_busy():
    all_rooms = [{"id": 1, "name": "301"}]
    busy_room_ids = {1}
    result = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)
    assert result == []


def test_all_rooms_free():
    all_rooms = [{"id": 1, "name": "301"}, {"id": 2, "name": "302"}]
    busy_room_ids = set()
    result = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)
    assert len(result) == 2
```

**Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_free_rooms.py -v
```

**Step 3: Add free rooms logic and endpoint to public.py**

Append to `backend/app/routers/public.py`:

```python
from sqlalchemy import select
from app.models import Card, Lesson


def _find_free_rooms_from_timetables(
    all_rooms: list[dict], busy_room_ids: set[int]
) -> list[dict]:
    return [r for r in all_rooms if r["id"] not in busy_room_ids]


@router.get("/rooms/free")
async def public_free_rooms(
    day: int = Query(default=0, ge=0, le=5, description="1=Пн..5=Пт, 0=сегодня"),
    period: int = Query(default=0, ge=0, le=10, description="1-10, 0=текущий"),
    db: AsyncSession = Depends(get_db),
):
    if day == 0:
        day = _get_today_weekday()
        if day == 0:
            return {"day": 0, "message": "Сегодня выходной", "free_rooms": []}

    if period == 0:
        now = datetime.now(MSK)
        period = _get_current_period(now.strftime("%H:%M"))
        if period == 0:
            return {"day": day, "period": 0, "message": "Сейчас нет уроков", "free_rooms": []}

    # Get all rooms
    all_rooms_result = await db.execute(select(Room).order_by(Room.name))
    all_rooms = [{"id": r.id, "name": r.name} for r in all_rooms_result.scalars().all()]

    # Get busy room IDs for this day+period
    busy_query = (
        select(Card.room_id)
        .where(Card.day == day, Card.period == period, Card.room_id.is_not(None))
    )
    busy_result = await db.execute(busy_query)
    busy_room_ids = {row[0] for row in busy_result.all()}

    # TODO Phase 3.2: also exclude room_bookings for this date

    free = _find_free_rooms_from_timetables(all_rooms, busy_room_ids)

    return {
        "day": day,
        "day_name": ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница"][day],
        "period": period,
        "time": PERIOD_TIMES.get(period, ""),
        "free_rooms": free,
        "total_rooms": len(all_rooms),
        "busy_rooms": len(busy_room_ids),
    }
```

**Step 4: Run tests — expect PASS**

```bash
pytest tests/test_free_rooms.py tests/test_public_api.py -v
```

**Step 5: Commit**

```bash
git add backend/app/routers/public.py backend/tests/test_free_rooms.py
git commit -m "feat: add free rooms endpoint to public API"
```

---

## Task 3: API key model + middleware

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/config.py`
- Create: `backend/app/middleware/api_key.py`
- New Alembic migration

**Step 1: Add ApiKey model**

Append to `backend/app/models.py`:

```python
import secrets


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))  # "unified-backend", "test-bot"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @staticmethod
    def generate_key() -> str:
        return secrets.token_urlsafe(32)
```

**Step 2: Create API key dependency**

Create `backend/app/middleware/__init__.py` (empty) and `backend/app/middleware/api_key.py`:

```python
from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required (X-API-Key header)",
        )

    key_obj = (
        await db.execute(select(ApiKey).where(ApiKey.key == api_key, ApiKey.is_active == True))
    ).scalar_one_or_none()

    if not key_obj:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key",
        )

    return key_obj
```

**Step 3: Generate migration**

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "add api_keys table"
alembic upgrade head
```

**Step 4: Commit**

```bash
cd ..
git add backend/app/models.py backend/app/middleware/ backend/alembic/versions/
git commit -m "feat: add API key model and middleware"
```

---

## Task 4: API key management endpoints (admin)

**Files:**
- Create: `backend/app/routers/api_keys.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Step 1: Add schemas**

Append to `backend/app/schemas.py`:

```python
class ApiKeyOut(BaseModel):
    id: int
    key: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
```

**Step 2: Create router**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey, User
from app.schemas import ApiKeyCreateRequest, ApiKeyOut
from app.security import get_current_user, require_role

router = APIRouter(
    prefix="/api/api-keys",
    tags=["api-keys"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=ApiKeyOut, status_code=201)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    key = ApiKey(
        key=ApiKey.generate_key(),
        name=payload.name.strip(),
        created_by_id=current_user.id,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=204)
async def deactivate_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
):
    key = await db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.commit()
```

**Step 3: Register in main.py**

```python
from app.routers import api_keys
app.include_router(api_keys.router)
```

**Step 4: Commit**

```bash
git add backend/app/routers/api_keys.py backend/app/schemas.py backend/app/main.py
git commit -m "feat: add API key management endpoints (admin)"
```

---

## Task 5: Room booking model + endpoints

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/routers/booking.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- New Alembic migration

**Step 1: Add RoomBooking model**

Append to `backend/app/models.py`:

```python
from sqlalchemy import Date


class RoomBooking(Base):
    __tablename__ = "room_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    day: Mapped[int] = mapped_column(Integer)  # 1-5 (weekday)
    period: Mapped[int] = mapped_column(Integer)  # 1-10
    date: Mapped[datetime] = mapped_column(Date)  # specific date, not permanent
    booked_by: Mapped[str] = mapped_column(String(200))  # "Иванов И.И." or "9А"
    purpose: Mapped[str | None] = mapped_column(String(300), nullable=True)
    api_key_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    room: Mapped[Room] = relationship()
```

**Step 2: Add schemas**

Append to `backend/app/schemas.py`:

```python
from datetime import date


class RoomBookingRequest(BaseModel):
    day: int = Field(ge=1, le=5)
    period: int = Field(ge=1, le=10)
    date: date
    booked_by: str = Field(min_length=1, max_length=200)
    purpose: str | None = Field(default=None, max_length=300)


class RoomBookingOut(BaseModel):
    id: int
    room_id: int
    room_name: str
    day: int
    period: int
    date: date
    booked_by: str
    purpose: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

**Step 3: Create booking router (API-key protected)**

```python
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.api_key import require_api_key
from app.models import ApiKey, Room, RoomBooking
from app.schemas import RoomBookingRequest, RoomBookingOut

router = APIRouter(prefix="/api/public/rooms", tags=["booking"])


@router.post("/{room_id}/book", status_code=201)
async def book_room(
    room_id: int,
    payload: RoomBookingRequest,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key),
):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check if already booked
    existing = (await db.execute(
        select(RoomBooking).where(
            RoomBooking.room_id == room_id,
            RoomBooking.date == payload.date,
            RoomBooking.period == payload.period,
        )
    )).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Room already booked by {existing.booked_by}",
        )

    booking = RoomBooking(
        room_id=room_id,
        day=payload.day,
        period=payload.period,
        date=payload.date,
        booked_by=payload.booked_by,
        purpose=payload.purpose,
        api_key_name=api_key.name,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    return {
        "id": booking.id,
        "room": room.name,
        "date": str(booking.date),
        "period": booking.period,
        "booked_by": booking.booked_by,
    }


@router.delete("/{room_id}/book/{booking_id}", status_code=204)
async def cancel_booking(
    room_id: int,
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: ApiKey = Depends(require_api_key),
):
    booking = await db.get(RoomBooking, booking_id)
    if not booking or booking.room_id != room_id:
        raise HTTPException(status_code=404, detail="Booking not found")

    await db.delete(booking)
    await db.commit()


@router.get("/{room_id}/bookings")
async def list_room_bookings(
    room_id: int,
    target_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(RoomBooking).where(RoomBooking.room_id == room_id)
    if target_date:
        query = query.where(RoomBooking.date == target_date)
    query = query.order_by(RoomBooking.date, RoomBooking.period)

    result = await db.execute(query)
    bookings = result.scalars().all()

    return [
        {
            "id": b.id,
            "period": b.period,
            "date": str(b.date),
            "booked_by": b.booked_by,
            "purpose": b.purpose,
        }
        for b in bookings
    ]
```

**Step 4: Update free rooms to check bookings**

In `backend/app/routers/public.py`, update `public_free_rooms` to also query bookings:

```python
from app.models import RoomBooking
from datetime import date as date_type

# Inside public_free_rooms, after getting busy_room_ids:
    today = datetime.now(MSK).date()
    booking_query = (
        select(RoomBooking.room_id)
        .where(RoomBooking.date == today, RoomBooking.day == day, RoomBooking.period == period)
    )
    booking_result = await db.execute(booking_query)
    booked_room_ids = {row[0] for row in booking_result.all()}
    busy_room_ids = busy_room_ids | booked_room_ids
```

**Step 5: Register and migrate**

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "add room_bookings table"
alembic upgrade head
```

In main.py:
```python
from app.routers import booking
app.include_router(booking.router)
```

**Step 6: Commit**

```bash
cd ..
git add backend/app/models.py backend/app/routers/booking.py backend/app/routers/public.py \
  backend/app/schemas.py backend/app/main.py backend/alembic/versions/
git commit -m "feat: add room booking with API key protection"
```

---

## Task 6: Frontend — API keys management panel

**Files:**
- Create: `frontend/src/components/ApiKeysPanel.tsx`
- Modify: `frontend/src/api/index.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/TopBar.tsx`

**Step 1: Add types**

Append to `frontend/src/types/index.ts`:

```typescript
export interface ApiKeyItem {
  id: number
  key: string
  name: string
  is_active: boolean
  created_at: string
}
```

**Step 2: Add API calls**

Append to `frontend/src/api/index.ts`:

```typescript
import type { ApiKeyItem } from '../types'

export async function getApiKeys(): Promise<ApiKeyItem[]> {
  const { data } = await api.get<ApiKeyItem[]>('/api-keys')
  return data
}

export async function createApiKey(name: string): Promise<ApiKeyItem> {
  const { data } = await api.post<ApiKeyItem>('/api-keys', { name })
  return data
}

export async function deactivateApiKey(id: number): Promise<void> {
  await api.delete(`/api-keys/${id}`)
}
```

**Step 3: Create ApiKeysPanel**

```tsx
import { useEffect, useState } from 'react'
import { createApiKey, deactivateApiKey, getApiKeys } from '../api'
import type { ApiKeyItem } from '../types'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ApiKeysPanel({ open, onClose }: Props) {
  const [keys, setKeys] = useState<ApiKeyItem[]>([])
  const [newName, setNewName] = useState('')
  const [copiedId, setCopiedId] = useState<number | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      getApiKeys().then(setKeys).catch(() => setError('Не удалось загрузить'))
    }
  }, [open])

  if (!open) return null

  const handleCreate = async () => {
    if (!newName.trim()) return
    setError('')
    try {
      const key = await createApiKey(newName.trim())
      setKeys([key, ...keys])
      setNewName('')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка')
    }
  }

  const handleDeactivate = async (id: number) => {
    await deactivateApiKey(id)
    setKeys(keys.map(k => k.id === id ? { ...k, is_active: false } : k))
  }

  const handleCopy = (key: ApiKeyItem) => {
    navigator.clipboard.writeText(key.key)
    setCopiedId(key.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ minWidth: 550 }}>
        <h3>API-ключи</h3>
        <p style={{ color: '#666', fontSize: 13, margin: '8px 0' }}>
          Ключи для интеграции с Telegram-ботами и внешними системами
        </p>

        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12, fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: 4 }}>Название</th>
              <th style={{ textAlign: 'left', padding: 4 }}>Ключ</th>
              <th style={{ padding: 4 }}>Статус</th>
              <th style={{ padding: 4 }}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <tr key={k.id}>
                <td style={{ padding: 4 }}>{k.name}</td>
                <td style={{ padding: 4, fontFamily: 'monospace', fontSize: 11 }}>
                  {k.key.substring(0, 12)}...
                  <button type="button" className="btn ghost" style={{ marginLeft: 4, fontSize: 11 }}
                    onClick={() => handleCopy(k)}>
                    {copiedId === k.id ? 'Скопировано!' : 'Копировать'}
                  </button>
                </td>
                <td style={{ padding: 4, textAlign: 'center' }}>
                  {k.is_active ? 'Активен' : 'Отключён'}
                </td>
                <td style={{ padding: 4, textAlign: 'center' }}>
                  {k.is_active && (
                    <button type="button" className="btn ghost" onClick={() => handleDeactivate(k.id)}>
                      Отключить
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <input placeholder="Название (напр. unified-bot)" value={newName}
            onChange={e => setNewName(e.target.value)} style={{ padding: 4, flex: 1 }} />
          <button type="button" className="btn" onClick={handleCreate}>Создать</button>
        </div>

        {error && <div style={{ color: 'red', marginTop: 8 }}>{error}</div>}

        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <button type="button" className="btn ghost" onClick={onClose}>Закрыть</button>
        </div>
      </div>
    </div>
  )
}
```

**Step 4: Wire into App.tsx and TopBar**

Add to TopBar props: `onApiKeysClick?: () => void`
Add button in TopBar (admin only):
```tsx
{role === 'admin' && onApiKeysClick && (
  <button type="button" className="btn ghost" onClick={onApiKeysClick}>API-ключи</button>
)}
```

In App.tsx:
```tsx
const [apiKeysOpen, setApiKeysOpen] = useState(false)
// TopBar: onApiKeysClick={() => setApiKeysOpen(true)}
// After other panels:
<ApiKeysPanel open={apiKeysOpen} onClose={() => setApiKeysOpen(false)} />
```

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add API keys management panel (admin)"
```

---

## Task 7: Telegram bot — scaffold (aiogram 3)

**Files:**
- Modify: `backend/requirements.txt` (add aiogram)
- Create: `backend/bot/__init__.py`
- Create: `backend/bot/config.py`
- Create: `backend/bot/client.py`
- Create: `backend/bot/main.py`

**Step 1: Add aiogram to requirements**

Append to `backend/requirements.txt`:

```
aiogram==3.15.0
```

**Step 2: Create bot config**

```python
"""Bot configuration. Reads from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    telegram_bot_token: str = ""
    ianus_api_url: str = "http://localhost:8000"
    ianus_api_key: str = ""  # For booking operations

    model_config = SettingsConfigDict(env_file=".env")


bot_settings = BotSettings()
```

**Step 3: Create API client**

```python
"""HTTP client for Ianus public API."""
from __future__ import annotations

import aiohttp
from bot.config import bot_settings


class IanusClient:
    def __init__(self):
        self.base = bot_settings.ianus_api_url.rstrip("/") + "/api/public"
        self.api_key = bot_settings.ianus_api_key

    async def _get(self, path: str) -> dict | list:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base}{path}") as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _post(self, path: str, data: dict) -> dict:
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base}{path}", json=data, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_classes(self) -> list[dict]:
        return await self._get("/classes")

    async def get_teachers(self) -> list[dict]:
        return await self._get("/teachers")

    async def get_class_timetable(self, class_id: int, day: int = 0) -> dict:
        return await self._get(f"/timetable/class/{class_id}?day={day}")

    async def get_teacher_timetable(self, teacher_id: int, day: int = 0) -> dict:
        return await self._get(f"/timetable/teacher/{teacher_id}?day={day}")

    async def get_teacher_now(self, teacher_id: int) -> dict:
        return await self._get(f"/teacher/{teacher_id}/now")

    async def get_free_rooms(self, day: int = 0, period: int = 0) -> dict:
        return await self._get(f"/rooms/free?day={day}&period={period}")

    async def book_room(self, room_id: int, data: dict) -> dict:
        return await self._post(f"/rooms/{room_id}/book", data)


ianus = IanusClient()
```

**Step 4: Create bot main**

```python
"""Telegram bot entry point — aiogram 3 polling mode."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from bot.config import bot_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher()


async def main():
    if not bot_settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        return

    bot = Bot(token=bot_settings.telegram_bot_token, parse_mode=ParseMode.HTML)

    # Import handlers (registered via decorators)
    from bot import handlers  # noqa: F401

    logger.info("Starting Ianus Telegram bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 5: Commit**

```bash
cd ..
git add backend/requirements.txt backend/bot/
git commit -m "feat: scaffold Telegram bot with aiogram 3 and Ianus API client"
```

---

## Task 8: Bot — registration (/start, role selection)

**Files:**
- Create: `backend/bot/storage.py`
- Create: `backend/bot/handlers/__init__.py`
- Create: `backend/bot/handlers/start.py`

**Step 1: Create simple file-based storage for bot users**

```python
"""Bot user storage — maps Telegram user ID to teacher/class.

Uses SQLite for simplicity (bot's own data, separate from main PostgreSQL).
"""
from __future__ import annotations

import json
from pathlib import Path

STORAGE_FILE = Path("bot/data/users.json")


def _load() -> dict:
    if STORAGE_FILE.exists():
        return json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
    return {}


def _save(data: dict):
    STORAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STORAGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user(telegram_id: int) -> dict | None:
    data = _load()
    return data.get(str(telegram_id))


def set_user(telegram_id: int, role: str, entity_id: int, entity_name: str):
    data = _load()
    data[str(telegram_id)] = {
        "role": role,  # "teacher" or "student"
        "entity_id": entity_id,
        "entity_name": entity_name,
    }
    _save(data)


def delete_user(telegram_id: int):
    data = _load()
    data.pop(str(telegram_id), None)
    _save(data)
```

**Step 2: Create start handler**

```python
"""Handler for /start and /reset — role selection and entity binding."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.client import ianus
from bot.storage import get_user, set_user, delete_user

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_user(message.from_user.id)
    if user:
        await message.answer(
            f"Вы уже зарегистрированы как <b>{user['entity_name']}</b> ({user['role']}).\n"
            f"Отправьте /reset чтобы перепривязаться."
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Я учитель", callback_data="role:teacher"),
            InlineKeyboardButton(text="Я ученик", callback_data="role:student"),
        ]
    ])
    await message.answer(
        "Добро пожаловать в <b>Ianus</b> — бот школьного расписания.\n\nКто вы?",
        reply_markup=keyboard,
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message):
    delete_user(message.from_user.id)
    await message.answer("Привязка сброшена. Отправьте /start для повторной регистрации.")


@router.callback_query(F.data == "role:teacher")
async def select_teacher(callback: CallbackQuery):
    teachers = await ianus.get_teachers()
    if not teachers:
        await callback.message.edit_text("Список учителей пуст. Сначала импортируйте расписание.")
        return

    # Show teachers in pages of 10
    buttons = []
    for t in teachers[:50]:  # limit to 50
        buttons.append([InlineKeyboardButton(
            text=t["short_name"] or t["name"],
            callback_data=f"bind:teacher:{t['id']}:{t['name'][:40]}",
        )])

    await callback.message.edit_text(
        "Выберите себя из списка:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data == "role:student")
async def select_class(callback: CallbackQuery):
    classes = await ianus.get_classes()
    if not classes:
        await callback.message.edit_text("Список классов пуст. Сначала импортируйте расписание.")
        return

    buttons = []
    row = []
    for c in classes:
        row.append(InlineKeyboardButton(
            text=c["name"],
            callback_data=f"bind:student:{c['id']}:{c['name']}",
        ))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await callback.message.edit_text(
        "Выберите свой класс:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("bind:"))
async def bind_entity(callback: CallbackQuery):
    _, role, entity_id_str, entity_name = callback.data.split(":", 3)
    entity_id = int(entity_id_str)

    set_user(callback.from_user.id, role, entity_id, entity_name)

    await callback.message.edit_text(
        f"Готово! Вы привязаны как <b>{entity_name}</b>.\n\n"
        f"Доступные команды:\n"
        f"/schedule — расписание на сегодня\n"
        f"/tomorrow — расписание на завтра\n"
        f"/next — следующий урок\n"
        f"/where — где сейчас учитель\n"
        f"/free — свободные кабинеты\n"
        f"/reset — сменить привязку"
    )
```

**Step 3: Create handlers __init__.py**

```python
"""Import all handler routers so they register with the dispatcher."""
from bot.handlers.start import router as start_router
from bot.handlers.schedule import router as schedule_router
from bot.handlers.search import router as search_router
from bot.main import dp

dp.include_router(start_router)
dp.include_router(schedule_router)
dp.include_router(search_router)
```

**Step 4: Commit**

```bash
git add backend/bot/
git commit -m "feat: add bot registration flow (/start, role selection)"
```

---

## Task 9: Bot — schedule commands

**Files:**
- Create: `backend/bot/handlers/schedule.py`

**Step 1: Implement schedule handlers**

```python
"""Schedule-related handlers: /schedule, /tomorrow, /next"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.client import ianus
from bot.storage import get_user

router = Router()

DAY_NAMES = {1: "Понедельник", 2: "Вторник", 3: "Среда", 4: "Четверг", 5: "Пятница"}


def _format_lessons(data: dict) -> str:
    if data.get("day") == 0:
        return "Сегодня выходной"

    lessons = data.get("lessons", [])
    if not lessons:
        day_name = data.get("day_name", "")
        return f"{day_name} — нет уроков"

    lines = [f"<b>{data.get('day_name', '')}</b> — {data.get('entity', '')}:\n"]
    for les in lessons:
        room = f" (каб. {les['room']})" if les.get("room") else ""
        teacher = f" — {les['teacher']}" if les.get("teacher") else ""
        group = f" [{les['group']}]" if les.get("group") else ""
        lines.append(f"  {les['period']}. <b>{les['subject']}</b>{teacher}{room}{group}")

    return "\n".join(lines)


async def _get_timetable(user: dict, day: int) -> dict:
    if user["role"] == "teacher":
        return await ianus.get_teacher_timetable(user["entity_id"], day)
    else:
        return await ianus.get_class_timetable(user["entity_id"], day)


def _require_user(message: Message) -> dict | None:
    user = get_user(message.from_user.id)
    return user


@router.message(Command("schedule"))
async def cmd_schedule(message: Message):
    user = _require_user(message)
    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    data = await _get_timetable(user, 0)  # 0 = today
    await message.answer(_format_lessons(data))


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message):
    user = _require_user(message)
    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    from datetime import datetime, timezone, timedelta
    MSK = timezone(timedelta(hours=3))
    today_wd = datetime.now(MSK).isoweekday()

    if today_wd >= 5:  # Friday or weekend → Monday
        next_day = 1
    else:
        next_day = today_wd + 1

    data = await _get_timetable(user, next_day)
    await message.answer(_format_lessons(data))


@router.message(Command("next"))
async def cmd_next(message: Message):
    user = _require_user(message)
    if not user:
        await message.answer("Сначала зарегистрируйтесь: /start")
        return

    data = await _get_timetable(user, 0)
    lessons = data.get("lessons", [])

    if not lessons:
        await message.answer("Сегодня уроков нет")
        return

    from datetime import datetime, timezone, timedelta
    MSK = timezone(timedelta(hours=3))
    now = datetime.now(MSK)
    current_minutes = now.hour * 60 + now.minute

    # Find next lesson by period time
    PERIOD_STARTS = [0, 510, 570, 630, 690, 745, 810, 875, 930, 985, 1040]  # minutes from midnight

    next_lesson = None
    for les in lessons:
        period = les["period"]
        if period < len(PERIOD_STARTS) and PERIOD_STARTS[period] > current_minutes:
            next_lesson = les
            break

    if not next_lesson:
        await message.answer("Уроки на сегодня закончились")
        return

    room = f"\nКабинет: {next_lesson['room']}" if next_lesson.get('room') else ""
    teacher = f"\n{next_lesson['teacher']}" if next_lesson.get('teacher') else ""
    await message.answer(
        f"Следующий урок ({next_lesson['period']}-й, {next_lesson.get('time', '')}):\n"
        f"<b>{next_lesson['subject']}</b>{teacher}{room}"
    )
```

**Step 2: Commit**

```bash
git add backend/bot/handlers/schedule.py
git commit -m "feat: add bot schedule commands (/schedule, /tomorrow, /next)"
```

---

## Task 10: Bot — search & free rooms commands

**Files:**
- Create: `backend/bot/handlers/search.py`

**Step 1: Implement search handlers**

```python
"""Search handlers: /where, /free, /book"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.client import ianus
from bot.storage import get_user

router = Router()


@router.message(Command("where"))
async def cmd_where(message: Message):
    """Show teacher search — pick teacher, see where they are now."""
    teachers = await ianus.get_teachers()
    if not teachers:
        await message.answer("Список учителей пуст")
        return

    # Show first 50 teachers as buttons
    buttons = []
    for t in teachers[:50]:
        buttons.append([InlineKeyboardButton(
            text=t["short_name"] or t["name"],
            callback_data=f"where:{t['id']}",
        )])

    await message.answer(
        "Выберите учителя:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("where:"))
async def where_teacher(callback: CallbackQuery):
    teacher_id = int(callback.data.split(":")[1])
    data = await ianus.get_teacher_now(teacher_id)

    status = data.get("status")
    teacher_name = data.get("teacher", "")

    if status == "weekend":
        text = "Сегодня выходной"
    elif status == "no_lesson":
        text = f"{teacher_name} — сейчас нет уроков"
    elif status == "free":
        text = f"{teacher_name} — урок {data['period']}, свободен"
    elif status == "teaching":
        room = f", каб. {data['room']}" if data.get("room") else ""
        text = (
            f"{teacher_name} — урок {data['period']} ({data.get('time', '')}):\n"
            f"<b>{data.get('subject', '')}</b>, класс {data.get('class', '')}{room}"
        )
    else:
        text = "Не удалось определить"

    await callback.message.edit_text(text)


@router.message(Command("free"))
async def cmd_free(message: Message):
    """Show free rooms for current period."""
    data = await ianus.get_free_rooms(day=0, period=0)

    if data.get("message"):
        await message.answer(data["message"])
        return

    free_rooms = data.get("free_rooms", [])
    day_name = data.get("day_name", "")
    period = data.get("period", 0)
    time = data.get("time", "")
    total = data.get("total_rooms", 0)

    if not free_rooms:
        await message.answer(f"{day_name}, урок {period} — все кабинеты заняты")
        return

    room_names = ", ".join(r["name"] for r in free_rooms[:20])
    if len(free_rooms) > 20:
        room_names += f" (+ещё {len(free_rooms) - 20})"

    await message.answer(
        f"<b>{day_name}, урок {period}</b> ({time})\n"
        f"Свободно {len(free_rooms)} из {total} кабинетов:\n\n"
        f"{room_names}"
    )
```

**Step 2: Commit**

```bash
git add backend/bot/handlers/search.py
git commit -m "feat: add bot /where and /free commands"
```

---

## Task 11: Bot — room booking command

**Files:**
- Modify: `backend/bot/handlers/search.py`

**Step 1: Add booking flow to search.py**

Append to `backend/bot/handlers/search.py`:

```python
from datetime import datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))


@router.message(Command("book"))
async def cmd_book(message: Message):
    """Start room booking flow — show free rooms for current period."""
    data = await ianus.get_free_rooms(day=0, period=0)

    if data.get("message"):
        await message.answer(data["message"])
        return

    free_rooms = data.get("free_rooms", [])
    period = data.get("period", 0)

    if not free_rooms:
        await message.answer("Нет свободных кабинетов на текущий урок")
        return

    buttons = []
    row = []
    for r in free_rooms[:24]:
        row.append(InlineKeyboardButton(
            text=r["name"],
            callback_data=f"book:{r['id']}:{period}",
        ))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await message.answer(
        f"Выберите кабинет для бронирования (урок {period}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("book:"))
async def do_book(callback: CallbackQuery):
    _, room_id_str, period_str = callback.data.split(":")
    room_id = int(room_id_str)
    period = int(period_str)

    user = get_user(callback.from_user.id)
    booked_by = user["entity_name"] if user else callback.from_user.full_name

    now = datetime.now(MSK)
    today = now.date().isoformat()
    weekday = now.isoweekday()

    try:
        result = await ianus.book_room(room_id, {
            "day": weekday,
            "period": period,
            "date": today,
            "booked_by": booked_by,
            "purpose": "Бронь через Telegram",
        })
        await callback.message.edit_text(
            f"Кабинет <b>{result.get('room', room_id)}</b> забронирован "
            f"на урок {period} ({today}) для {booked_by}"
        )
    except Exception:
        await callback.message.edit_text("Не удалось забронировать — возможно, кабинет уже занят")
```

**Step 2: Commit**

```bash
git add backend/bot/handlers/search.py
git commit -m "feat: add bot /book command for room booking"
```

---

## Task 12: Bot documentation + .env.example update

**Files:**
- Modify: `.env.example`
- Update: `backend/bot/handlers/__init__.py` (fix imports)

**Step 1: Update .env.example**

Append:

```env
# Telegram bot
TELEGRAM_BOT_TOKEN=
IANUS_API_URL=http://localhost:8000
IANUS_API_KEY=
```

**Step 2: Final bot handlers __init__.py**

```python
from bot.handlers.start import router as start_router
from bot.handlers.schedule import router as schedule_router
from bot.handlers.search import router as search_router
from bot.main import dp

dp.include_router(start_router)
dp.include_router(schedule_router)
dp.include_router(search_router)
```

**Step 3: Commit**

```bash
git add .env.example backend/bot/
git commit -m "feat: finalize bot setup and documentation"
```

---

## Task Summary

| # | Task | Scope |
|---|------|-------|
| 1 | Public API — lists + timetable by day + teacher now | Backend |
| 2 | Free rooms endpoint | Backend |
| 3 | API key model + middleware | Backend |
| 4 | API key management endpoints (admin) | Backend |
| 5 | Room booking model + endpoints | Backend |
| 6 | Frontend — API keys panel | Frontend |
| 7 | Telegram bot scaffold (aiogram 3) | Bot |
| 8 | Bot — registration (/start, /reset) | Bot |
| 9 | Bot — /schedule, /tomorrow, /next | Bot |
| 10 | Bot — /where, /free | Bot |
| 11 | Bot — /book (room booking) | Bot |
| 12 | .env.example + final wiring | Config |
