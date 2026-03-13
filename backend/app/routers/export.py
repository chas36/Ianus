from __future__ import annotations

import os
import sys
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.timetable import timetable_by_class, timetable_by_room, timetable_by_teacher
from app.schemas import TimetableResponse
from app.security import get_current_user
from app.services.audit import log_action
from app.services.export_service import timetable_to_pdf_html, timetable_to_xlsx

router = APIRouter(
    prefix="/api/export",
    tags=["export"],
    dependencies=[Depends(get_current_user)],
)


def _prepare_weasyprint_runtime() -> None:
    if sys.platform != "darwin":
        return

    homebrew_lib = "/opt/homebrew/lib"
    if not os.path.isdir(homebrew_lib):
        return

    current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if homebrew_lib in current.split(":"):
        return

    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
        f"{current}:{homebrew_lib}".strip(":")
    )


async def _export(tt: TimetableResponse, fmt: Literal["xlsx", "pdf"], name: str) -> Response:
    if fmt == "xlsx":
        data = timetable_to_xlsx(tt)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{name}.xlsx"'},
        )

    try:
        _prepare_weasyprint_runtime()
        from weasyprint import HTML
    except (ImportError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "PDF export is unavailable in current environment. "
                "Install WeasyPrint system dependencies (pango/cairo/gobject)."
            ),
        ) from exc

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
    current_user: User = Depends(get_current_user),
) -> Response:
    tt = await timetable_by_class(class_id, db)
    await log_action(
        db,
        "export",
        detail=f"Export class {tt.entity_name} as {format}",
        user=current_user,
    )
    await db.commit()
    return await _export(tt, format, f"class_{class_id}")


@router.get("/teacher/{teacher_id}")
async def export_teacher(
    teacher_id: int,
    format: Literal["xlsx", "pdf"] = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    tt = await timetable_by_teacher(teacher_id, db)
    await log_action(
        db,
        "export",
        detail=f"Export teacher {tt.entity_name} as {format}",
        user=current_user,
    )
    await db.commit()
    return await _export(tt, format, f"teacher_{teacher_id}")


@router.get("/room/{room_id}")
async def export_room(
    room_id: int,
    format: Literal["xlsx", "pdf"] = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    tt = await timetable_by_room(room_id, db)
    await log_action(
        db,
        "export",
        detail=f"Export room {tt.entity_name} as {format}",
        user=current_user,
    )
    await db.commit()
    return await _export(tt, format, f"room_{room_id}")
