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
        await db.execute(
            select(ApiKey).where(
                ApiKey.key == api_key,
                ApiKey.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()

    if not key_obj:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or inactive API key",
        )

    return key_obj
