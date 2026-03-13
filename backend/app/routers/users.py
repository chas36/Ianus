from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import UserCreateRequest, UserOut, UserUpdateRequest
from app.security import get_current_user, get_password_hash, require_role
from app.services.audit import log_action

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[UserOut])
async def list_users(db: AsyncSession = Depends(get_db)) -> list[User]:
    result = await db.execute(select(User).order_by(User.username))
    return list(result.scalars().all())


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    username = payload.username.strip()
    existing = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    user = User(
        username=username,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    await log_action(
        db,
        "create_user",
        detail=f"Created user {user.username} ({user.role})",
        user=current_user,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        user.password_hash = get_password_hash(payload.password)

    await log_action(
        db,
        "update_user",
        detail=f"Updated user {user.username}",
        user=current_user,
    )
    await db.commit()
    await db.refresh(user)
    return user
