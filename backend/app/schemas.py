from __future__ import annotations

from pydantic import BaseModel, Field


class SubjectOut(BaseModel):
    id: int
    name: str
    short_name: str

    model_config = {"from_attributes": True}


class TeacherOut(BaseModel):
    id: int
    name: str
    short_name: str
    color: str | None = None

    model_config = {"from_attributes": True}


class ClassOut(BaseModel):
    id: int
    name: str
    short_name: str

    model_config = {"from_attributes": True}


class RoomOut(BaseModel):
    id: int
    name: str
    short_name: str

    model_config = {"from_attributes": True}


class TimetableCell(BaseModel):
    subject: str
    teacher: str | None = None
    room: str | None = None
    group: str | None = None


class TimetableRow(BaseModel):
    period: int
    time: str
    days: dict[int, list[TimetableCell]]


class TimetableResponse(BaseModel):
    entity_type: str
    entity_name: str
    rows: list[TimetableRow]


class ImportResponse(BaseModel):
    subjects: int
    teachers: int
    classes: int
    rooms: int
    lessons: int
    cards: int


class AuthBootstrapRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=120)


class AuthBootstrapResponse(BaseModel):
    id: int
    username: str
    role: str


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str


class AuthMeResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
