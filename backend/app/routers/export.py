from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.timetable import timetable_by_class, timetable_by_room, timetable_by_teacher
from app.schemas import TimetableResponse
from app.services.export_service import timetable_to_pdf_html, timetable_to_xlsx

router = APIRouter(prefix="/api/export", tags=["export"])


async def _export(tt: TimetableResponse, fmt: Literal["xlsx", "pdf"], name: str) -> Response:
    if fmt == "xlsx":
        data = timetable_to_xlsx(tt)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
        )

    from weasyprint import HTML

    html = timetable_to_pdf_html(tt)
    pdf_bytes = HTML(string=html).write_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'},
    )


@router.get("/class/{class_id}")
async def export_class(
    class_id: int,
    format: Literal["xlsx", "pdf"] = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    tt = await timetable_by_class(class_id, db)
    return await _export(tt, format, f"class_{tt.entity_name}")


@router.get("/teacher/{teacher_id}")
async def export_teacher(
    teacher_id: int,
    format: Literal["xlsx", "pdf"] = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    tt = await timetable_by_teacher(teacher_id, db)
    return await _export(tt, format, f"teacher_{tt.entity_name}")


@router.get("/room/{room_id}")
async def export_room(
    room_id: int,
    format: Literal["xlsx", "pdf"] = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    tt = await timetable_by_room(room_id, db)
    return await _export(tt, format, f"room_{tt.entity_name}")
