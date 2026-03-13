from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User


async def log_action(
    db: AsyncSession,
    action: str,
    detail: str | None = None,
    user: User | None = None,
) -> None:
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "system",
        action=action,
        detail=detail,
    )
    db.add(entry)
