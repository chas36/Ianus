# Ianus MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Web platform for viewing and exporting school timetable imported from aSc Timetables XML.

**Architecture:** FastAPI backend parses aSc XML, stores in PostgreSQL via SQLAlchemy. React frontend displays timetable grid (days x periods) with 3 view modes (class/teacher/room). Export to Excel/PDF via backend endpoints.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, asyncpg, React 18, TypeScript, Vite, openpyxl, weasyprint, Docker Compose, PostgreSQL 16.

## Progress Tracking (Updated: 2026-03-12)

- [x] Task 1: Docker Compose + PostgreSQL (files created; runtime check blocked by local Docker daemon)
- [x] Task 2: Backend skeleton (FastAPI + SQLAlchemy)
- [x] Task 3: Database models (SQLAlchemy ORM)
- [x] Task 4: Alembic migrations (initialized + initial migration created; offline SQL generated)
- [x] Task 5: aSc XML parser service + tests
- [x] Task 6: Pydantic schemas
- [x] Task 7: Import API endpoint (implemented; DB runtime check pending)
- [x] Task 8: Timetable API endpoints (implemented; DB runtime check pending)
- [x] Task 9: Export service (Excel + PDF) (XLSX/PDF verified in runtime)
- [x] Task 10: Frontend setup (React + Vite + TypeScript)
- [x] Task 11: Frontend API layer + types
- [x] Task 12: Frontend TopBar component
- [x] Task 13: Frontend Sidebar component
- [x] Task 14: Frontend TimetableGrid component
- [x] Task 15: Frontend ImportDialog component
- [x] Task 16: Frontend App wiring

## Phase 2 Extension (Started: 2026-03-12)

- [x] P2.1: JWT auth foundation (users table, bootstrap/login/me, protected API)
- [ ] P2.2: Role separation (admin/teacher permissions)
- [ ] P2.3: UI role-aware visibility and actions
- [ ] P2.4: Audit trail for imports/exports and timetable access

---

## Task 1: Docker Compose + PostgreSQL

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Node
node_modules/
dist/

# Environment
.env

# IDE
.idea/
.vscode/

# Database
pgdata/
```

**Step 2: Create .env.example**

```env
POSTGRES_USER=ianus
POSTGRES_PASSWORD=ianus_dev
POSTGRES_DB=ianus
DATABASE_URL=postgresql+asyncpg://ianus:ianus_dev@localhost:5432/ianus
```

**Step 3: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ianus}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ianus_dev}
      POSTGRES_DB: ${POSTGRES_DB:-ianus}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**Step 4: Start PostgreSQL and verify**

Run: `cp .env.example .env && docker compose up -d db`
Then: `docker compose exec db psql -U ianus -c "SELECT 1"`
Expected: connection successful

**Step 5: Commit**

```bash
git add .gitignore .env.example docker-compose.yml
git commit -m "infra: add docker-compose with PostgreSQL"
```

---

## Task 2: Backend skeleton (FastAPI + SQLAlchemy)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/database.py`
- Create: `backend/app/config.py`

**Step 1: Create requirements.txt**

```txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.1
python-multipart==0.0.18
openpyxl==3.1.5
weasyprint==63.1
pydantic-settings==2.7.1
```

**Step 2: Create backend/app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ianus:ianus_dev@localhost:5432/ianus"

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 3: Create backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session
```

**Step 4: Create backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ianus", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 5: Create venv and verify**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
python -m uvicorn backend.app.main:app --port 8000 &
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
kill %1
```

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add FastAPI backend skeleton"
```

---

## Task 3: Database models (SQLAlchemy ORM)

**Files:**
- Create: `backend/app/models.py`

**Step 1: Create models.py with all 7 tables**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Float, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    source_format: Mapped[str] = mapped_column(String(50))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    asc_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(100))


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    asc_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(10))


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    asc_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    short_name: Mapped[str] = mapped_column(String(50))


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    asc_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str] = mapped_column(String(100))


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    asc_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"))
    group_name: Mapped[str | None] = mapped_column(String(100))
    periods_per_week: Mapped[float] = mapped_column(Float, default=1.0)

    subject: Mapped["Subject"] = relationship()
    teacher: Mapped["Teacher | None"] = relationship()
    school_class: Mapped["SchoolClass"] = relationship()
    cards: Mapped[list["Card"]] = relationship(back_populates="lesson")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    day: Mapped[int] = mapped_column(Integer)  # 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт
    period: Mapped[int] = mapped_column(Integer)  # 1-10

    lesson: Mapped["Lesson"] = relationship(back_populates="cards")
    room: Mapped["Room | None"] = relationship()
```

**Step 2: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add SQLAlchemy ORM models for timetable"
```

---

## Task 4: Alembic migrations

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (auto-generated)

**Step 1: Initialize Alembic**

```bash
cd backend
source .venv/bin/activate
alembic init alembic
```

**Step 2: Edit alembic.ini — set sqlalchemy.url**

In `backend/alembic.ini`, change:
```
sqlalchemy.url = postgresql://ianus:ianus_dev@localhost:5432/ianus
```

**Step 3: Edit alembic/env.py — import models**

At the top of `backend/alembic/env.py`, add after existing imports:
```python
from app.models import Base
target_metadata = Base.metadata
```
Replace the existing `target_metadata = None` line.

**Step 4: Generate and run migration**

```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```

**Step 5: Verify tables exist**

```bash
docker compose exec db psql -U ianus -c "\dt"
```
Expected: tables subjects, teachers, classes, rooms, lessons, cards, imports, alembic_version

**Step 6: Commit**

```bash
cd ..
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic migrations with initial schema"
```

---

## Task 5: aSc XML parser service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/asc_xml_parser.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_asc_xml_parser.py`

**Step 1: Write the test**

```python
"""Tests for aSc Timetables XML parser."""
import pytest
from app.services.asc_xml_parser import parse_asc_xml

# Minimal valid XML for testing
SAMPLE_XML = """\
<?xml version="1.0" encoding="windows-1251"?>
<timetable ascttversion="2024.24.1" importtype="database">
   <periods columns="period,name,short,starttime,endtime">
      <period name="1" short="1" period="1" starttime="8:30" endtime="9:15"/>
      <period name="2" short="2" period="2" starttime="9:30" endtime="10:15"/>
   </periods>
   <subjects columns="id,name,short,partner_id">
      <subject id="SUBJ1" name="Математика" short="Мат" partner_id=""/>
      <subject id="SUBJ2" name="Физика" short="Физ" partner_id=""/>
   </subjects>
   <teachers columns="id,name,short,gender,color,email,mobile,partner_id,firstname,lastname">
      <teacher id="TCH1" name="Иванов Иван Иванович" short="Иванов И.И."
               gender="M" color="#FF0000" email="" mobile="" partner_id=""
               firstname="Иван Иванович" lastname="Иванов"/>
   </teachers>
   <classes columns="id,name,short,classroomids,teacherid,grade,partner_id">
      <class id="CLS1" name="5А" short="5А" teacherid="TCH1"
             classroomids="ROOM1" grade="" partner_id=""/>
   </classes>
   <classrooms columns="id,name,short,capacity,buildingid,partner_id">
      <classroom id="ROOM1" name="301" short="301" capacity="*"
                 buildingid="" partner_id=""/>
   </classrooms>
   <groups columns="id,classid,name,entireclass,divisiontag,studentcount,studentids">
      <group id="GRP1" name="Весь класс" classid="CLS1"
             entireclass="1" divisiontag="0" studentids="" studentcount=""/>
      <group id="GRP2" name="1 группа" classid="CLS1"
             entireclass="0" divisiontag="1" studentids="" studentcount=""/>
   </groups>
   <lessons columns="id,subjectid,classids,groupids,teacherids,classroomids,periodspercard,periodsperweek,daysdefid,weeksdefid,termsdefid,seminargroup,capacity,partner_id">
      <lesson id="LES1" classids="CLS1" subjectid="SUBJ1" periodspercard="1"
              periodsperweek="3.0" teacherids="TCH1" classroomids="ROOM1"
              groupids="GRP1" capacity="*" seminargroup=""
              termsdefid="" weeksdefid="" daysdefid="" partner_id=""/>
      <lesson id="LES2" classids="CLS1" subjectid="SUBJ2" periodspercard="1"
              periodsperweek="2.0" teacherids="TCH1" classroomids="ROOM1"
              groupids="GRP2" capacity="*" seminargroup=""
              termsdefid="" weeksdefid="" daysdefid="" partner_id=""/>
   </lessons>
   <cards columns="lessonid,period,days,weeks,terms,classroomids">
      <card lessonid="LES1" classroomids="ROOM1" period="1" weeks="11" terms="1" days="10000"/>
      <card lessonid="LES1" classroomids="ROOM1" period="2" weeks="11" terms="1" days="01000"/>
      <card lessonid="LES1" classroomids="ROOM1" period="1" weeks="11" terms="1" days="00100"/>
      <card lessonid="LES2" classroomids="ROOM1" period="2" weeks="11" terms="1" days="10000"/>
      <card lessonid="LES2" classroomids="ROOM1" period="1" weeks="11" terms="1" days="01000"/>
   </cards>
</timetable>
""".encode("windows-1251")


def test_parse_subjects():
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["subjects"]) == 2
    assert result["subjects"][0] == {
        "asc_id": "SUBJ1", "name": "Математика", "short_name": "Мат",
    }


def test_parse_teachers():
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["teachers"]) == 1
    assert result["teachers"][0]["name"] == "Иванов Иван Иванович"
    assert result["teachers"][0]["color"] == "#FF0000"


def test_parse_classes():
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "5А"


def test_parse_rooms():
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["rooms"]) == 1
    assert result["rooms"][0]["name"] == "301"


def test_parse_lessons():
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["lessons"]) == 2
    les1 = result["lessons"][0]
    assert les1["asc_id"] == "LES1"
    assert les1["subject_asc_id"] == "SUBJ1"
    assert les1["teacher_asc_id"] == "TCH1"
    assert les1["class_asc_id"] == "CLS1"
    assert les1["periods_per_week"] == 3.0


def test_parse_cards():
    result = parse_asc_xml(SAMPLE_XML)
    assert len(result["cards"]) == 5
    card0 = result["cards"][0]
    assert card0["lesson_asc_id"] == "LES1"
    assert card0["room_asc_id"] == "ROOM1"
    assert card0["day"] == 1  # "10000" -> Monday
    assert card0["period"] == 1


def test_parse_cards_day_mapping():
    result = parse_asc_xml(SAMPLE_XML)
    days = [c["day"] for c in result["cards"]]
    # LES1: Mon(1), Tue(2), Wed(3); LES2: Mon(1), Tue(2)
    assert days == [1, 2, 3, 1, 2]


def test_parse_lesson_group_name():
    result = parse_asc_xml(SAMPLE_XML)
    les2 = result["lessons"][1]
    assert les2["group_name"] == "1 группа"


def test_parse_lesson_whole_class_group():
    result = parse_asc_xml(SAMPLE_XML)
    les1 = result["lessons"][0]
    assert les1["group_name"] is None  # entireclass=1 -> no group name
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate
pip install pytest
pytest tests/test_asc_xml_parser.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.asc_xml_parser'`

**Step 3: Implement the parser**

```python
"""Parser for aSc Timetables XML export format.

aSc XML structure:
- <subjects>/<subject>: id, name, short
- <teachers>/<teacher>: id, name, short, color
- <classes>/<class>: id, name, short
- <classrooms>/<classroom>: id, name, short
- <groups>/<group>: id, classid, name, entireclass
- <lessons>/<lesson>: id, subjectid, classids, teacherids, groupids, classroomids, periodsperweek
- <cards>/<card>: lessonid, period, days (bitfield "10000"=Mon), classroomids

Encoding: windows-1251
"""
from xml.etree import ElementTree as ET


DAY_BITS = {"10000": 1, "01000": 2, "00100": 3, "00010": 4, "00001": 5}


def parse_asc_xml(xml_bytes: bytes) -> dict:
    text = xml_bytes.decode("windows-1251")
    root = ET.fromstring(text)

    # Build group lookup: group_id -> {name, entireclass}
    groups_by_id = {}
    for g in root.findall(".//group"):
        groups_by_id[g.get("id")] = {
            "name": g.get("name", ""),
            "entireclass": g.get("entireclass") == "1",
        }

    subjects = [
        {"asc_id": s.get("id"), "name": s.get("name", ""), "short_name": s.get("short", "")}
        for s in root.findall(".//subject")
    ]

    teachers = [
        {
            "asc_id": t.get("id"),
            "name": t.get("name", ""),
            "short_name": t.get("short", ""),
            "color": t.get("color"),
        }
        for t in root.findall(".//teacher")
    ]

    classes = [
        {"asc_id": c.get("id"), "name": c.get("name", ""), "short_name": c.get("short", "")}
        for c in root.findall(".//class")
    ]

    rooms = [
        {"asc_id": r.get("id"), "name": r.get("name", ""), "short_name": r.get("short", "")}
        for r in root.findall(".//classroom")
    ]

    lessons = []
    for les in root.findall(".//lesson"):
        # First teacher and first class (most common case)
        teacher_ids = les.get("teacherids", "").split(",")
        class_ids = les.get("classids", "").split(",")
        group_ids = les.get("groupids", "").split(",")

        # Resolve group name: skip if entireclass=1
        group_name = None
        for gid in group_ids:
            gid = gid.strip()
            if gid and gid in groups_by_id:
                grp = groups_by_id[gid]
                if not grp["entireclass"]:
                    group_name = grp["name"]
                    break

        lessons.append({
            "asc_id": les.get("id"),
            "subject_asc_id": les.get("subjectid", ""),
            "teacher_asc_id": teacher_ids[0].strip() if teacher_ids[0].strip() else None,
            "class_asc_id": class_ids[0].strip() if class_ids[0].strip() else None,
            "group_name": group_name,
            "periods_per_week": float(les.get("periodsperweek", "1.0")),
        })

    cards = []
    for card in root.findall(".//card"):
        days_str = card.get("days", "")
        day = DAY_BITS.get(days_str, 0)
        room_ids = card.get("classroomids", "").split(",")
        cards.append({
            "lesson_asc_id": card.get("lessonid", ""),
            "room_asc_id": room_ids[0].strip() if room_ids[0].strip() else None,
            "day": day,
            "period": int(card.get("period", "0")),
        })

    return {
        "subjects": subjects,
        "teachers": teachers,
        "classes": classes,
        "rooms": rooms,
        "lessons": lessons,
        "cards": cards,
    }
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_asc_xml_parser.py -v
```
Expected: all 8 tests PASS

**Step 5: Commit**

```bash
cd ..
git add backend/app/services/ backend/tests/
git commit -m "feat: add aSc XML parser with tests"
```

---

## Task 6: Pydantic schemas

**Files:**
- Create: `backend/app/schemas.py`

**Step 1: Create schemas.py**

```python
from pydantic import BaseModel


class SubjectOut(BaseModel):
    id: int
    name: str
    short_name: str

    class Config:
        from_attributes = True


class TeacherOut(BaseModel):
    id: int
    name: str
    short_name: str
    color: str | None = None

    class Config:
        from_attributes = True


class ClassOut(BaseModel):
    id: int
    name: str
    short_name: str

    class Config:
        from_attributes = True


class RoomOut(BaseModel):
    id: int
    name: str
    short_name: str

    class Config:
        from_attributes = True


class TimetableCell(BaseModel):
    subject: str
    teacher: str | None = None
    room: str | None = None
    group: str | None = None


class TimetableRow(BaseModel):
    period: int
    time: str  # "8:30 - 9:15"
    days: dict[int, list[TimetableCell]]  # day -> cells (list for split lessons)


class TimetableResponse(BaseModel):
    entity_type: str  # "class", "teacher", "room"
    entity_name: str
    rows: list[TimetableRow]


class ImportResponse(BaseModel):
    subjects: int
    teachers: int
    classes: int
    rooms: int
    lessons: int
    cards: int
```

**Step 2: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat: add Pydantic schemas"
```

---

## Task 7: Import API endpoint

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/import_router.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Create import_router.py**

```python
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Card, Import, Lesson, Room, SchoolClass, Subject, Teacher
from app.schemas import ImportResponse
from app.services.asc_xml_parser import parse_asc_xml

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/asc-xml", response_model=ImportResponse)
async def import_asc_xml(file: UploadFile, db: AsyncSession = Depends(get_db)):
    xml_bytes = await file.read()
    data = parse_asc_xml(xml_bytes)

    # Upsert subjects
    subj_map = {}  # asc_id -> db id
    for s in data["subjects"]:
        existing = (await db.execute(
            select(Subject).where(Subject.asc_id == s["asc_id"])
        )).scalar_one_or_none()
        if existing:
            existing.name = s["name"]
            existing.short_name = s["short_name"]
            obj = existing
        else:
            obj = Subject(**s)
            db.add(obj)
        await db.flush()
        subj_map[s["asc_id"]] = obj.id

    # Upsert teachers
    teacher_map = {}
    for t in data["teachers"]:
        existing = (await db.execute(
            select(Teacher).where(Teacher.asc_id == t["asc_id"])
        )).scalar_one_or_none()
        if existing:
            existing.name = t["name"]
            existing.short_name = t["short_name"]
            existing.color = t["color"]
            obj = existing
        else:
            obj = Teacher(**t)
            db.add(obj)
        await db.flush()
        teacher_map[t["asc_id"]] = obj.id

    # Upsert classes
    class_map = {}
    for c in data["classes"]:
        existing = (await db.execute(
            select(SchoolClass).where(SchoolClass.asc_id == c["asc_id"])
        )).scalar_one_or_none()
        if existing:
            existing.name = c["name"]
            existing.short_name = c["short_name"]
            obj = existing
        else:
            obj = SchoolClass(**c)
            db.add(obj)
        await db.flush()
        class_map[c["asc_id"]] = obj.id

    # Upsert rooms
    room_map = {}
    for r in data["rooms"]:
        existing = (await db.execute(
            select(Room).where(Room.asc_id == r["asc_id"])
        )).scalar_one_or_none()
        if existing:
            existing.name = r["name"]
            existing.short_name = r["short_name"]
            obj = existing
        else:
            obj = Room(**r)
            db.add(obj)
        await db.flush()
        room_map[r["asc_id"]] = obj.id

    # Upsert lessons
    lesson_map = {}
    for les in data["lessons"]:
        subj_id = subj_map.get(les["subject_asc_id"])
        teacher_id = teacher_map.get(les["teacher_asc_id"])
        class_id = class_map.get(les["class_asc_id"])
        if not subj_id or not class_id:
            continue

        existing = (await db.execute(
            select(Lesson).where(Lesson.asc_id == les["asc_id"])
        )).scalar_one_or_none()
        if existing:
            existing.subject_id = subj_id
            existing.teacher_id = teacher_id
            existing.class_id = class_id
            existing.group_name = les["group_name"]
            existing.periods_per_week = les["periods_per_week"]
            obj = existing
        else:
            obj = Lesson(
                asc_id=les["asc_id"],
                subject_id=subj_id,
                teacher_id=teacher_id,
                class_id=class_id,
                group_name=les["group_name"],
                periods_per_week=les["periods_per_week"],
            )
            db.add(obj)
        await db.flush()
        lesson_map[les["asc_id"]] = obj.id

    # Delete old cards and insert new
    await db.execute(Card.__table__.delete())
    card_count = 0
    for c in data["cards"]:
        lesson_id = lesson_map.get(c["lesson_asc_id"])
        if not lesson_id or c["day"] == 0:
            continue
        room_id = room_map.get(c["room_asc_id"])
        db.add(Card(
            lesson_id=lesson_id,
            room_id=room_id,
            day=c["day"],
            period=c["period"],
        ))
        card_count += 1

    # Record import
    db.add(Import(filename=file.filename or "unknown", source_format="asc-xml"))

    await db.commit()

    return ImportResponse(
        subjects=len(data["subjects"]),
        teachers=len(data["teachers"]),
        classes=len(data["classes"]),
        rooms=len(data["rooms"]),
        lessons=len(data["lessons"]),
        cards=card_count,
    )
```

**Step 2: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.routers import import_router

app.include_router(import_router.router)
```

**Step 3: Test import manually**

```bash
# Start backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 &

# Upload XML
curl -X POST http://localhost:8000/api/import/asc-xml \
  -F "file=@../export_file/import.xml"
```
Expected: `{"subjects":102,"teachers":71,"classes":51,"rooms":78,"lessons":679,"cards":...}`

**Step 4: Commit**

```bash
cd ..
git add backend/app/routers/ backend/app/main.py
git commit -m "feat: add XML import endpoint with upsert logic"
```

---

## Task 8: Timetable API endpoints

**Files:**
- Create: `backend/app/routers/timetable.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Create timetable.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Card, Lesson, Room, SchoolClass, Subject, Teacher
from app.schemas import (
    ClassOut, RoomOut, TeacherOut,
    TimetableCell, TimetableResponse, TimetableRow,
)

router = APIRouter(prefix="/api", tags=["timetable"])

PERIOD_TIMES = {
    1: "8:30 - 9:15", 2: "9:30 - 10:15", 3: "10:30 - 11:15",
    4: "11:30 - 12:15", 5: "12:25 - 13:10", 6: "13:30 - 14:15",
    7: "14:35 - 15:20", 8: "15:30 - 16:15", 9: "16:25 - 17:10",
    10: "17:20 - 18:05",
}


@router.get("/classes", response_model=list[ClassOut])
async def list_classes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchoolClass).order_by(SchoolClass.name))
    return result.scalars().all()


@router.get("/teachers", response_model=list[TeacherOut])
async def list_teachers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Teacher).order_by(Teacher.name))
    return result.scalars().all()


@router.get("/rooms", response_model=list[RoomOut])
async def list_rooms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).order_by(Room.name))
    return result.scalars().all()


async def _build_timetable(cards_query, entity_type: str, entity_name: str, db, cell_builder):
    result = await db.execute(cards_query)
    cards = result.unique().scalars().all()

    grid: dict[int, dict[int, list[TimetableCell]]] = {}
    for card in cards:
        lesson = card.lesson
        cell = cell_builder(card, lesson)
        grid.setdefault(card.period, {}).setdefault(card.day, []).append(cell)

    rows = []
    for period in range(1, 11):
        days_data = {}
        for day in range(1, 6):
            days_data[day] = grid.get(period, {}).get(day, [])
        rows.append(TimetableRow(
            period=period,
            time=PERIOD_TIMES.get(period, ""),
            days=days_data,
        ))

    return TimetableResponse(entity_type=entity_type, entity_name=entity_name, rows=rows)


@router.get("/timetable/class/{class_id}", response_model=TimetableResponse)
async def timetable_by_class(class_id: int, db: AsyncSession = Depends(get_db)):
    cls = await db.get(SchoolClass, class_id)
    if not cls:
        raise HTTPException(404, "Class not found")

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

    def cell_builder(card, lesson):
        return TimetableCell(
            subject=lesson.subject.name,
            teacher=lesson.teacher.name if lesson.teacher else None,
            room=card.room.name if card.room else None,
            group=lesson.group_name,
        )

    return await _build_timetable(query, "class", cls.name, db, cell_builder)


@router.get("/timetable/teacher/{teacher_id}", response_model=TimetableResponse)
async def timetable_by_teacher(teacher_id: int, db: AsyncSession = Depends(get_db)):
    teacher = await db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(404, "Teacher not found")

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

    def cell_builder(card, lesson):
        return TimetableCell(
            subject=lesson.subject.name,
            teacher=lesson.school_class.name,  # show class instead of teacher
            room=card.room.name if card.room else None,
            group=lesson.group_name,
        )

    return await _build_timetable(query, "teacher", teacher.name, db, cell_builder)


@router.get("/timetable/room/{room_id}", response_model=TimetableResponse)
async def timetable_by_room(room_id: int, db: AsyncSession = Depends(get_db)):
    room = await db.get(Room, room_id)
    if not room:
        raise HTTPException(404, "Room not found")

    query = (
        select(Card)
        .where(Card.room_id == room_id)
        .options(
            selectinload(Card.lesson).selectinload(Lesson.subject),
            selectinload(Card.lesson).selectinload(Lesson.school_class),
            selectinload(Card.lesson).selectinload(Lesson.teacher),
        )
    )

    def cell_builder(card, lesson):
        return TimetableCell(
            subject=lesson.subject.name,
            teacher=lesson.school_class.name,  # show class
            room=lesson.teacher.short_name if lesson.teacher else None,  # show teacher
            group=lesson.group_name,
        )

    return await _build_timetable(query, "room", room.name, db, cell_builder)
```

**Step 2: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.routers import timetable

app.include_router(timetable.router)
```

**Step 3: Test manually**

```bash
curl http://localhost:8000/api/classes
curl http://localhost:8000/api/timetable/class/1
```

**Step 4: Commit**

```bash
git add backend/app/routers/timetable.py backend/app/main.py
git commit -m "feat: add timetable API endpoints (class/teacher/room)"
```

---

## Task 9: Export service (Excel + PDF)

**Files:**
- Create: `backend/app/services/export_service.py`
- Create: `backend/app/routers/export.py`
- Modify: `backend/app/main.py` (register router)

**Step 1: Create export_service.py**

```python
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.schemas import TimetableResponse

DAY_NAMES = {1: "Понедельник", 2: "Вторник", 3: "Среда", 4: "Четверг", 5: "Пятница"}


def timetable_to_xlsx(tt: TimetableResponse) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = tt.entity_name

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="CCE5FF", fill_type="solid")

    # Title
    ws.merge_cells("A1:F1")
    ws["A1"] = f"{tt.entity_type.upper()}: {tt.entity_name}"
    ws["A1"].font = Font(bold=True, size=14)

    # Column headers
    ws["A3"] = "Урок"
    ws["A3"].font = header_font
    for day in range(1, 6):
        col = chr(65 + day)  # B, C, D, E, F
        cell = ws[f"{col}3"]
        cell.value = DAY_NAMES[day]
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[col].width = 28

    ws.column_dimensions["A"].width = 8

    # Data rows
    for row_idx, row in enumerate(tt.rows, start=4):
        ws[f"A{row_idx}"] = row.period
        ws[f"A{row_idx}"].font = Font(bold=True)
        ws[f"A{row_idx}"].border = border
        ws[f"A{row_idx}"].alignment = Alignment(horizontal="center")

        for day in range(1, 6):
            col = chr(65 + day)
            cell = ws[f"{col}{row_idx}"]
            cells = row.days.get(day, [])
            if cells:
                lines = []
                for c in cells:
                    parts = [c.subject]
                    if c.teacher:
                        parts.append(c.teacher)
                    if c.room:
                        parts.append(f"каб. {c.room}")
                    if c.group:
                        parts.append(f"({c.group})")
                    lines.append(" | ".join(parts))
                cell.value = "\n".join(lines)
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def timetable_to_pdf_html(tt: TimetableResponse) -> str:
    rows_html = ""
    for row in tt.rows:
        cells = f"<td class='period'>{row.period}<br><small>{row.time}</small></td>"
        for day in range(1, 6):
            entries = row.days.get(day, [])
            if entries:
                inner = "<br>".join(
                    f"<b>{c.subject}</b>"
                    + (f"<br>{c.teacher}" if c.teacher else "")
                    + (f"<br><i>каб. {c.room}</i>" if c.room else "")
                    + (f"<br>({c.group})" if c.group else "")
                    for c in entries
                )
            else:
                inner = ""
            cells += f"<td>{inner}</td>"
        rows_html += f"<tr>{cells}</tr>"

    day_headers = "".join(f"<th>{DAY_NAMES[d]}</th>" for d in range(1, 6))

    return f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 11px; }}
  h1 {{ font-size: 16px; text-align: center; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ border: 1px solid #333; padding: 4px; vertical-align: top; }}
  th {{ background: #CCE5FF; text-align: center; }}
  td.period {{ text-align: center; font-weight: bold; width: 50px; }}
  small {{ color: #666; }}
</style></head>
<body>
<h1>{tt.entity_name}</h1>
<table>
<tr><th>Урок</th>{day_headers}</tr>
{rows_html}
</table>
</body></html>"""
```

**Step 2: Create export router**

```python
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.timetable import timetable_by_class, timetable_by_room, timetable_by_teacher
from app.services.export_service import timetable_to_pdf_html, timetable_to_xlsx

router = APIRouter(prefix="/api/export", tags=["export"])


async def _export(tt, fmt: str, name: str):
    if fmt == "xlsx":
        data = timetable_to_xlsx(tt)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
        )
    elif fmt == "pdf":
        from weasyprint import HTML
        html = timetable_to_pdf_html(tt)
        pdf_bytes = HTML(string=html).write_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'},
        )
    return Response(status_code=400, content="Unsupported format")


@router.get("/class/{class_id}")
async def export_class(
    class_id: int,
    format: str = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
):
    tt = await timetable_by_class(class_id, db)
    return await _export(tt, format, f"class_{tt.entity_name}")


@router.get("/teacher/{teacher_id}")
async def export_teacher(
    teacher_id: int,
    format: str = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
):
    tt = await timetable_by_teacher(teacher_id, db)
    return await _export(tt, format, f"teacher_{tt.entity_name}")


@router.get("/room/{room_id}")
async def export_room(
    room_id: int,
    format: str = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
):
    tt = await timetable_by_room(room_id, db)
    return await _export(tt, format, f"room_{tt.entity_name}")
```

**Step 3: Register in main.py**

```python
from app.routers import export
app.include_router(export.router)
```

**Step 4: Test**

```bash
curl -o test.xlsx http://localhost:8000/api/export/class/1?format=xlsx
```

**Step 5: Commit**

```bash
git add backend/app/services/export_service.py backend/app/routers/export.py backend/app/main.py
git commit -m "feat: add Excel and PDF export"
```

---

## Task 10: Frontend — project setup (React + Vite + TypeScript)

**Files:**
- Create: `frontend/` via `npm create vite`

**Step 1: Scaffold Vite project**

```bash
cd /Users/neelylew/Documents/Projects/web/Ianus
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install axios
```

**Step 2: Configure Vite proxy to backend**

Edit `frontend/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

**Step 3: Verify dev server**

```bash
npm run dev
# Open http://localhost:5173 in browser
```

**Step 4: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold React frontend with Vite"
```

---

## Task 11: Frontend — API layer + types

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/index.ts`

**Step 1: Create types**

```typescript
export interface ClassItem {
  id: number
  name: string
  short_name: string
}

export interface TeacherItem {
  id: number
  name: string
  short_name: string
  color?: string
}

export interface RoomItem {
  id: number
  name: string
  short_name: string
}

export interface TimetableCell {
  subject: string
  teacher: string | null
  room: string | null
  group: string | null
}

export interface TimetableRow {
  period: number
  time: string
  days: Record<number, TimetableCell[]>
}

export interface TimetableResponse {
  entity_type: string
  entity_name: string
  rows: TimetableRow[]
}

export interface ImportResponse {
  subjects: number
  teachers: number
  classes: number
  rooms: number
  lessons: number
  cards: number
}

export type ViewMode = 'class' | 'teacher' | 'room'
```

**Step 2: Create API client**

```typescript
import axios from 'axios'
import type {
  ClassItem, TeacherItem, RoomItem,
  TimetableResponse, ImportResponse,
} from '../types'

const api = axios.create({ baseURL: '/api' })

export async function getClasses(): Promise<ClassItem[]> {
  const { data } = await api.get('/classes')
  return data
}

export async function getTeachers(): Promise<TeacherItem[]> {
  const { data } = await api.get('/teachers')
  return data
}

export async function getRooms(): Promise<RoomItem[]> {
  const { data } = await api.get('/rooms')
  return data
}

export async function getTimetable(
  mode: string, id: number
): Promise<TimetableResponse> {
  const { data } = await api.get(`/timetable/${mode}/${id}`)
  return data
}

export async function importXml(file: File): Promise<ImportResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/import/asc-xml', form)
  return data
}

export function getExportUrl(mode: string, id: number, format: string): string {
  return `/api/export/${mode}/${id}?format=${format}`
}
```

**Step 3: Commit**

```bash
git add frontend/src/types/ frontend/src/api/
git commit -m "feat: add TypeScript types and API client"
```

---

## Task 12: Frontend — TopBar component

**Files:**
- Create: `frontend/src/components/TopBar.tsx`

**Step 1: Create TopBar**

```tsx
import type { ViewMode } from '../types'

interface Props {
  mode: ViewMode
  onModeChange: (mode: ViewMode) => void
  selectedId: number | null
  onImportClick: () => void
  onExport: (format: string) => void
}

const MODES: { key: ViewMode; label: string }[] = [
  { key: 'class', label: 'Классы' },
  { key: 'teacher', label: 'Учителя' },
  { key: 'room', label: 'Кабинеты' },
]

export default function TopBar({ mode, onModeChange, selectedId, onImportClick, onExport }: Props) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '8px 16px', borderBottom: '1px solid #ddd', background: '#f5f5f5',
    }}>
      <div style={{ display: 'flex', gap: 4 }}>
        {MODES.map(m => (
          <button
            key={m.key}
            onClick={() => onModeChange(m.key)}
            style={{
              padding: '6px 16px', cursor: 'pointer',
              background: mode === m.key ? '#1976d2' : '#fff',
              color: mode === m.key ? '#fff' : '#333',
              border: '1px solid #ccc', borderRadius: 4,
              fontWeight: mode === m.key ? 600 : 400,
            }}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1 }} />
      <button onClick={onImportClick} style={{ padding: '6px 16px', cursor: 'pointer' }}>
        Импорт XML
      </button>
      {selectedId && (
        <>
          <button onClick={() => onExport('xlsx')} style={{ padding: '6px 16px', cursor: 'pointer' }}>
            Excel
          </button>
          <button onClick={() => onExport('pdf')} style={{ padding: '6px 16px', cursor: 'pointer' }}>
            PDF
          </button>
        </>
      )}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/TopBar.tsx
git commit -m "feat: add TopBar component with mode switcher and export buttons"
```

---

## Task 13: Frontend — Sidebar component

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`

**Step 1: Create Sidebar**

```tsx
import type { ClassItem, TeacherItem, RoomItem, ViewMode } from '../types'

interface Props {
  mode: ViewMode
  classes: ClassItem[]
  teachers: TeacherItem[]
  rooms: RoomItem[]
  selectedId: number | null
  onSelect: (id: number) => void
}

export default function Sidebar({ mode, classes, teachers, rooms, selectedId, onSelect }: Props) {
  const items = mode === 'class' ? classes
    : mode === 'teacher' ? teachers
    : rooms

  // Group classes by grade (first chars before letter)
  const grouped = mode === 'class'
    ? Object.groupBy(classes, c => c.name.match(/^\d+/)?.[0] ?? '')
    : null

  return (
    <div style={{
      width: 180, borderRight: '1px solid #ddd', overflowY: 'auto',
      padding: 8, background: '#fafafa',
    }}>
      {grouped ? (
        Object.entries(grouped).map(([grade, items]) => (
          <div key={grade} style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: 600, fontSize: 12, color: '#666', padding: '4px 0' }}>
              {grade} класс
            </div>
            {(items ?? []).map(item => (
              <SidebarItem key={item.id} item={item} selected={selectedId === item.id} onSelect={onSelect} />
            ))}
          </div>
        ))
      ) : (
        items.map(item => (
          <SidebarItem key={item.id} item={item} selected={selectedId === item.id} onSelect={onSelect} />
        ))
      )}
    </div>
  )
}

function SidebarItem({ item, selected, onSelect }: {
  item: { id: number; name: string }; selected: boolean; onSelect: (id: number) => void
}) {
  return (
    <div
      onClick={() => onSelect(item.id)}
      style={{
        padding: '4px 8px', cursor: 'pointer', borderRadius: 4,
        background: selected ? '#1976d2' : 'transparent',
        color: selected ? '#fff' : '#333',
        fontSize: 13,
      }}
    >
      {item.name}
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/Sidebar.tsx
git commit -m "feat: add Sidebar with grouped class list"
```

---

## Task 14: Frontend — TimetableGrid component

**Files:**
- Create: `frontend/src/components/TimetableGrid.tsx`

**Step 1: Create TimetableGrid**

```tsx
import type { TimetableResponse } from '../types'

const DAY_NAMES = ['', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']

// Subject -> color mapping (deterministic hash)
function subjectColor(subject: string): string {
  let hash = 0
  for (let i = 0; i < subject.length; i++) {
    hash = subject.charCodeAt(i) + ((hash << 5) - hash)
  }
  const h = Math.abs(hash) % 360
  return `hsl(${h}, 55%, 85%)`
}

interface Props {
  timetable: TimetableResponse | null
}

export default function TimetableGrid({ timetable }: Props) {
  if (!timetable) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
        Выберите элемент в боковой панели
      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
      <h2 style={{ margin: '0 0 8px', fontSize: 16 }}>{timetable.entity_name}</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr>
            <th style={thStyle}>Урок</th>
            {[1, 2, 3, 4, 5].map(d => (
              <th key={d} style={{ ...thStyle, width: '19%' }}>{DAY_NAMES[d]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {timetable.rows.map(row => (
            <tr key={row.period}>
              <td style={{ ...tdStyle, textAlign: 'center', fontWeight: 600 }}>
                {row.period}
                <br />
                <small style={{ color: '#888', fontWeight: 400 }}>{row.time}</small>
              </td>
              {[1, 2, 3, 4, 5].map(day => {
                const cells = row.days[day] ?? []
                return (
                  <td key={day} style={{
                    ...tdStyle,
                    background: cells.length === 1 ? subjectColor(cells[0].subject) : undefined,
                  }}>
                    {cells.map((c, i) => (
                      <div key={i} style={{
                        padding: 2,
                        background: cells.length > 1 ? subjectColor(c.subject) : undefined,
                        borderRadius: cells.length > 1 ? 3 : 0,
                        marginBottom: cells.length > 1 && i < cells.length - 1 ? 2 : 0,
                      }}>
                        <div style={{ fontWeight: 600 }}>{c.subject}</div>
                        {c.teacher && <div>{c.teacher}</div>}
                        {c.room && <div style={{ color: '#555' }}>каб. {c.room}</div>}
                        {c.group && <div style={{ fontStyle: 'italic', color: '#666' }}>({c.group})</div>}
                      </div>
                    ))}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const thStyle: React.CSSProperties = {
  border: '1px solid #ccc', padding: 6, background: '#e3f2fd', textAlign: 'center',
}

const tdStyle: React.CSSProperties = {
  border: '1px solid #ddd', padding: 4, verticalAlign: 'top', minHeight: 50,
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/TimetableGrid.tsx
git commit -m "feat: add TimetableGrid with color-coded cells"
```

---

## Task 15: Frontend — ImportDialog component

**Files:**
- Create: `frontend/src/components/ImportDialog.tsx`

**Step 1: Create ImportDialog**

```tsx
import { useRef, useState } from 'react'
import { importXml } from '../api'
import type { ImportResponse } from '../types'

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function ImportDialog({ open, onClose, onSuccess }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportResponse | null>(null)
  const [error, setError] = useState('')

  if (!open) return null

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setLoading(true)
    setError('')
    try {
      const res = await importXml(file)
      setResult(res)
      onSuccess()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка импорта')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }}>
      <div style={{ background: '#fff', borderRadius: 8, padding: 24, minWidth: 400 }}>
        <h3 style={{ margin: '0 0 16px' }}>Импорт из aSc Timetables</h3>
        <input ref={fileRef} type="file" accept=".xml" />
        <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
          <button onClick={handleUpload} disabled={loading}
            style={{ padding: '6px 20px', cursor: 'pointer' }}>
            {loading ? 'Загрузка...' : 'Импортировать'}
          </button>
          <button onClick={onClose} style={{ padding: '6px 20px', cursor: 'pointer' }}>
            Закрыть
          </button>
        </div>
        {error && <div style={{ color: 'red', marginTop: 8 }}>{error}</div>}
        {result && (
          <div style={{ marginTop: 12, padding: 12, background: '#e8f5e9', borderRadius: 4 }}>
            Загружено: {result.subjects} предметов, {result.teachers} учителей,
            {result.classes} классов, {result.rooms} кабинетов,
            {result.lessons} уроков, {result.cards} карточек
          </div>
        )}
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/ImportDialog.tsx
git commit -m "feat: add ImportDialog for XML upload"
```

---

## Task 16: Frontend — App.tsx (wire everything together)

**Files:**
- Modify: `frontend/src/App.tsx`
- Delete: `frontend/src/App.css` (unused)

**Step 1: Rewrite App.tsx**

```tsx
import { useCallback, useEffect, useState } from 'react'
import { getClasses, getExportUrl, getRooms, getTeachers, getTimetable } from './api'
import ImportDialog from './components/ImportDialog'
import Sidebar from './components/Sidebar'
import TimetableGrid from './components/TimetableGrid'
import TopBar from './components/TopBar'
import type { ClassItem, RoomItem, TeacherItem, TimetableResponse, ViewMode } from './types'

export default function App() {
  const [mode, setMode] = useState<ViewMode>('class')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [timetable, setTimetable] = useState<TimetableResponse | null>(null)
  const [classes, setClasses] = useState<ClassItem[]>([])
  const [teachers, setTeachers] = useState<TeacherItem[]>([])
  const [rooms, setRooms] = useState<RoomItem[]>([])
  const [importOpen, setImportOpen] = useState(false)

  const loadLists = useCallback(async () => {
    const [c, t, r] = await Promise.all([getClasses(), getTeachers(), getRooms()])
    setClasses(c)
    setTeachers(t)
    setRooms(r)
  }, [])

  useEffect(() => { loadLists() }, [loadLists])

  useEffect(() => { setSelectedId(null); setTimetable(null) }, [mode])

  useEffect(() => {
    if (selectedId == null) { setTimetable(null); return }
    getTimetable(mode, selectedId).then(setTimetable)
  }, [mode, selectedId])

  const handleExport = (format: string) => {
    if (selectedId == null) return
    window.open(getExportUrl(mode, selectedId, format))
  }

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <TopBar
        mode={mode}
        onModeChange={setMode}
        selectedId={selectedId}
        onImportClick={() => setImportOpen(true)}
        onExport={handleExport}
      />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar
          mode={mode}
          classes={classes}
          teachers={teachers}
          rooms={rooms}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <TimetableGrid timetable={timetable} />
      </div>
      <ImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={loadLists}
      />
    </div>
  )
}
```

**Step 2: Clean up index.css**

Replace `frontend/src/index.css` with:
```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
```

**Step 3: Test end-to-end**

1. `docker compose up -d db`
2. `cd backend && source .venv/bin/activate && alembic upgrade head && uvicorn app.main:app --reload --port 8000 &`
3. `cd frontend && npm run dev`
4. Open http://localhost:5173
5. Click "Импорт XML" -> upload `export_file/import.xml`
6. Select a class in sidebar -> see timetable grid
7. Click "Excel" -> download .xlsx

**Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/index.css
git commit -m "feat: wire up App with all components - MVP complete"
```

---

## Task Summary

| # | Task | Scope |
|---|------|-------|
| 1 | Docker Compose + PostgreSQL | Infra |
| 2 | Backend skeleton (FastAPI) | Backend |
| 3 | Database models (ORM) | Backend |
| 4 | Alembic migrations | Backend |
| 5 | aSc XML parser + tests | Backend |
| 6 | Pydantic schemas | Backend |
| 7 | Import API endpoint | Backend |
| 8 | Timetable API endpoints | Backend |
| 9 | Export service (Excel/PDF) | Backend |
| 10 | Frontend setup (Vite) | Frontend |
| 11 | API layer + types | Frontend |
| 12 | TopBar component | Frontend |
| 13 | Sidebar component | Frontend |
| 14 | TimetableGrid component | Frontend |
| 15 | ImportDialog component | Frontend |
| 16 | App.tsx (wire everything) | Frontend |
