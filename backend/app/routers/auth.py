from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import (
    AuthBootstrapRequest,
    AuthBootstrapResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
)
from app.security import authenticate_user, create_access_token, get_current_user, get_password_hash
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/bootstrap-required")
async def bootstrap_required(db: AsyncSession = Depends(get_db)) -> dict[str, bool]:
    users_count = await db.scalar(select(func.count(User.id)))
    return {"required": (users_count or 0) == 0}


@router.post("/bootstrap", response_model=AuthBootstrapResponse)
async def bootstrap_admin(
    payload: AuthBootstrapRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthBootstrapResponse:
    users_count = await db.scalar(select(func.count(User.id)))
    if (users_count or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bootstrap already completed",
        )

    user = User(
        username=payload.username.strip(),
        password_hash=get_password_hash(payload.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return AuthBootstrapResponse(id=user.id, username=user.username, role=user.role)


@router.post("/login", response_model=AuthLoginResponse)
async def login(
    payload: AuthLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthLoginResponse:
    user = await authenticate_user(db, payload.username.strip(), payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token(subject=user.username)
    await log_action(db, "login", detail=f"User {user.username} logged in", user=user)
    await db.commit()
    return AuthLoginResponse(access_token=token, token_type="bearer")


@router.get("/me", response_model=AuthMeResponse)
async def me(current_user: User = Depends(get_current_user)) -> AuthMeResponse:
    return AuthMeResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )
