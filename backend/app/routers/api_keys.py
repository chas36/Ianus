from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApiKey, User
from app.schemas import ApiKeyCreateRequest, ApiKeyOut
from app.security import get_current_user, require_role
from app.services.audit import log_action

router = APIRouter(
    prefix="/api/api-keys",
    tags=["api-keys"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(db: AsyncSession = Depends(get_db)) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=ApiKeyOut, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiKey:
    key = ApiKey(
        key=ApiKey.generate_key(),
        name=payload.name.strip(),
        created_by_id=current_user.id,
        is_active=True,
    )
    db.add(key)
    await db.flush()

    await log_action(
        db,
        "create_api_key",
        detail=f"Created API key {key.name}",
        user=current_user,
    )
    await db.commit()
    await db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def deactivate_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    key = await db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    key.is_active = False

    await log_action(
        db,
        "deactivate_api_key",
        detail=f"Deactivated API key {key.name}",
        user=current_user,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
