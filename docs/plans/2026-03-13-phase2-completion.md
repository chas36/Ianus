# Phase 2 Completion: Roles, Permissions & Audit Trail

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete Phase 2 — add role-based access (admin creates users, teacher views only own timetable), UI adapts to role, all actions logged to audit trail.

**Architecture:** Extend existing JWT auth with `require_role()` dependency. Admin can manage users and import. Teachers see only their own schedule. AuditLog table records all significant actions. Frontend conditionally renders UI based on `currentUser.role`.

**Tech Stack:** Same as MVP — FastAPI, SQLAlchemy, Alembic, React, TypeScript.

**Existing state:**
- User model has `role` field (String(20), default="admin")
- `get_current_user` dependency returns authenticated User
- Import/timetable/export routers require auth via `dependencies=[Depends(get_current_user)]`
- Frontend knows `currentUser.role` from `/api/auth/me`

## Execution Status (Updated: 2026-03-13)

- [x] Task 1: `require_role` dependency + tests
- [x] Task 2: Import endpoint restricted to `admin`
- [x] Task 3: Admin user management endpoints (`/api/users`)
- [x] Task 4: `audit_log` model + migration
- [x] Task 5: Audit service (`log_action`)
- [x] Task 6: Audit wiring in auth/import/export/users endpoints
- [x] Task 7: Audit API endpoint (`/api/audit`, admin-only)
- [x] Task 8: Role-aware TopBar
- [x] Task 9: Users management panel (admin-only)
- [x] Task 10: Audit panel (admin-only)
- [x] Task 11: Teacher restrictions decision (read allowed, write admin-only)

---

## Task 1: Role-checking dependency

**Files:**
- Modify: `backend/app/security.py`
- Create: `backend/tests/test_security.py`

**Step 1: Write the test**

```python
"""Tests for role-based access control."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.security import require_role
from app.models import User


def _make_user(role: str) -> User:
    user = MagicMock(spec=User)
    user.role = role
    user.username = "testuser"
    user.is_active = True
    return user


def test_require_role_admin_passes():
    checker = require_role("admin")
    user = _make_user("admin")
    result = checker(user)
    assert result is user


def test_require_role_admin_blocks_teacher():
    checker = require_role("admin")
    user = _make_user("teacher")
    with pytest.raises(HTTPException) as exc_info:
        checker(user)
    assert exc_info.value.status_code == 403


def test_require_role_teacher_passes():
    checker = require_role("admin", "teacher")
    user = _make_user("teacher")
    result = checker(user)
    assert result is user


def test_require_role_multiple_roles():
    checker = require_role("admin", "teacher")
    admin = _make_user("admin")
    assert checker(admin) is admin
    teacher = _make_user("teacher")
    assert checker(teacher) is teacher
```

**Step 2: Run tests — expect FAIL**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_security.py -v
```
Expected: `AttributeError: module 'app.security' has no attribute 'require_role'`

**Step 3: Implement require_role in security.py**

Add at the end of `backend/app/security.py`:

```python
def require_role(*allowed_roles: str):
    """FastAPI dependency factory that checks user role.

    Usage: Depends(require_role("admin"))
    Usage: Depends(require_role("admin", "teacher"))
    """
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return checker
```

**Step 4: Run tests — expect PASS**

```bash
pytest tests/test_security.py -v
```

**Step 5: Commit**

```bash
git add backend/app/security.py backend/tests/test_security.py
git commit -m "feat: add require_role dependency for RBAC"
```

---

## Task 2: Protect import endpoint (admin-only)

**Files:**
- Modify: `backend/app/routers/import_router.py`

**Step 1: Change router dependency to admin-only**

In `backend/app/routers/import_router.py`, change:

```python
# OLD:
from app.security import get_current_user

router = APIRouter(
    prefix="/api/import",
    tags=["import"],
    dependencies=[Depends(get_current_user)],
)
```

to:

```python
# NEW:
from app.security import require_role

router = APIRouter(
    prefix="/api/import",
    tags=["import"],
    dependencies=[Depends(require_role("admin"))],
)
```

**Step 2: Commit**

```bash
git add backend/app/routers/import_router.py
git commit -m "feat: restrict import endpoint to admin role"
```

---

## Task 3: Admin user management endpoints

**Files:**
- Create: `backend/app/routers/users.py`
- Modify: `backend/app/schemas.py` (add user schemas)
- Modify: `backend/app/main.py` (register router)

**Step 1: Add Pydantic schemas**

Append to `backend/app/schemas.py`:

```python
class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=120)
    role: str = Field(default="teacher", pattern="^(admin|teacher)$")


class UserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|teacher)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=120)
```

**Step 2: Create users router**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import UserCreateRequest, UserOut, UserUpdateRequest
from app.security import get_password_hash, require_role

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
) -> User:
    existing = (
        await db.execute(select(User).where(User.username == payload.username.strip()))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    user = User(
        username=payload.username.strip(),
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
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

    await db.commit()
    await db.refresh(user)
    return user
```

**Step 3: Register in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import auth, export, import_router, timetable, users

app.include_router(users.router)
```

**Step 4: Commit**

```bash
git add backend/app/routers/users.py backend/app/schemas.py backend/app/main.py
git commit -m "feat: add admin user management endpoints (CRUD)"
```

---

## Task 4: AuditLog model + migration

**Files:**
- Modify: `backend/app/models.py`
- Create: new Alembic migration

**Step 1: Add AuditLog model**

Append to `backend/app/models.py`:

```python
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(50))  # login, import, export, create_user, etc.
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

**Step 2: Generate migration**

```bash
cd backend && source .venv/bin/activate
alembic revision --autogenerate -m "add audit_log table"
```

**Step 3: Apply migration**

```bash
alembic upgrade head
```

**Step 4: Commit**

```bash
cd ..
git add backend/app/models.py backend/alembic/versions/
git commit -m "feat: add AuditLog model and migration"
```

---

## Task 5: Audit logging service

**Files:**
- Create: `backend/app/services/audit.py`

**Step 1: Create audit service**

```python
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
    # Don't commit here — caller controls the transaction
```

**Step 2: Commit**

```bash
git add backend/app/services/audit.py
git commit -m "feat: add audit logging service"
```

---

## Task 6: Wire audit into existing endpoints

**Files:**
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/app/routers/import_router.py`
- Modify: `backend/app/routers/export.py`
- Modify: `backend/app/routers/users.py`

**Step 1: Add audit to login**

In `backend/app/routers/auth.py`, in the `login` function, after creating the token:

```python
from app.services.audit import log_action

# After: token = create_access_token(...)
await log_action(db, "login", detail=f"User {user.username} logged in", user=user)
await db.commit()
```

**Step 2: Add audit to import**

In `backend/app/routers/import_router.py`, inject current user and log:

```python
from app.models import User
from app.security import get_current_user, require_role
from app.services.audit import log_action

# Change function signature to include user:
async def import_asc_xml(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImportResponse:
    # ... existing code ...
    # Before: await db.commit()
    await log_action(
        db, "import",
        detail=f"Imported {file.filename}: {len(data['subjects'])} subjects, {cards_count} cards",
        user=current_user,
    )
    await db.commit()
```

**Step 3: Add audit to export**

In `backend/app/routers/export.py`, add user and audit to each export function:

```python
from app.models import User
from app.security import get_current_user
from app.services.audit import log_action

# In each export endpoint, add current_user param and log:
async def export_class(
    class_id: int,
    format: str = Query("xlsx"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tt = await timetable_by_class(class_id, db)
    await log_action(db, "export", detail=f"Export class {tt.entity_name} as {format}", user=current_user)
    await db.commit()
    return await _export(tt, format, f"class_{tt.entity_name}")
```

(Same pattern for `export_teacher` and `export_room`.)

**Step 4: Add audit to user management**

In `backend/app/routers/users.py`, in `create_user`:

```python
from app.services.audit import log_action
from app.security import get_current_user

# Add current_user param:
async def create_user(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    # ... existing code ...
    # After db.commit():
    await log_action(db, "create_user", detail=f"Created user {user.username} ({user.role})", user=current_user)
    await db.commit()
```

**Step 5: Commit**

```bash
git add backend/app/routers/
git commit -m "feat: wire audit logging into all endpoints"
```

---

## Task 7: Audit log API endpoint

**Files:**
- Create: `backend/app/routers/audit.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Step 1: Add schema**

Append to `backend/app/schemas.py`:

```python
from datetime import datetime


class AuditLogOut(BaseModel):
    id: int
    username: str
    action: str
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

**Step 2: Create audit router**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut
from app.security import require_role

router = APIRouter(
    prefix="/api/audit",
    tags=["audit"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())
```

**Step 3: Register in main.py**

```python
from app.routers import audit
app.include_router(audit.router)
```

**Step 4: Commit**

```bash
git add backend/app/routers/audit.py backend/app/schemas.py backend/app/main.py
git commit -m "feat: add audit log API endpoint (admin-only)"
```

---

## Task 8: Frontend — role-aware TopBar

**Files:**
- Modify: `frontend/src/components/TopBar.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Pass role to TopBar and hide admin-only buttons**

In `frontend/src/components/TopBar.tsx`, add `role` prop and conditionally render:

```tsx
interface TopBarProps {
  mode: ViewMode
  selectedId: number | null
  currentUsername: string
  role: string  // <-- NEW
  onModeChange: (mode: ViewMode) => void
  onImportClick: () => void
  onExport: (format: 'xlsx' | 'pdf') => void
  onLogout: () => void
  onUsersClick?: () => void  // <-- NEW
  onAuditClick?: () => void  // <-- NEW
}
```

In the JSX, wrap admin-only buttons:

```tsx
{role === 'admin' && (
  <button type="button" className="btn ghost" onClick={onImportClick}>
    Импорт XML
  </button>
)}
{role === 'admin' && onUsersClick && (
  <button type="button" className="btn ghost" onClick={onUsersClick}>
    Пользователи
  </button>
)}
{role === 'admin' && onAuditClick && (
  <button type="button" className="btn ghost" onClick={onAuditClick}>
    Журнал
  </button>
)}
```

**Step 2: Pass role from App.tsx**

In `frontend/src/App.tsx`, change TopBar usage:

```tsx
<TopBar
  mode={mode}
  selectedId={selectedId}
  currentUsername={`${currentUser.username} (${currentUser.role})`}
  role={currentUser.role}
  onModeChange={setMode}
  onImportClick={() => setImportOpen(true)}
  onExport={(format) => void handleExport(format)}
  onLogout={handleLogout}
/>
```

**Step 3: Commit**

```bash
git add frontend/src/components/TopBar.tsx frontend/src/App.tsx
git commit -m "feat: hide admin-only buttons from teacher role"
```

---

## Task 9: Frontend — Users management panel (admin)

**Files:**
- Create: `frontend/src/components/UsersPanel.tsx`
- Modify: `frontend/src/api/index.ts` (add user API calls)
- Modify: `frontend/src/types/index.ts` (add user types)
- Modify: `frontend/src/App.tsx` (wire panel)

**Step 1: Add types**

Append to `frontend/src/types/index.ts`:

```typescript
export interface UserItem {
  id: number
  username: string
  role: string
  is_active: boolean
}

export interface UserCreateRequest {
  username: string
  password: string
  role: string
}
```

**Step 2: Add API calls**

Append to `frontend/src/api/index.ts`:

```typescript
import type { UserItem, UserCreateRequest } from '../types'

export async function getUsers(): Promise<UserItem[]> {
  const { data } = await api.get<UserItem[]>('/users')
  return data
}

export async function createUser(payload: UserCreateRequest): Promise<UserItem> {
  const { data } = await api.post<UserItem>('/users', payload)
  return data
}

export async function updateUser(
  id: number, payload: { role?: string; is_active?: boolean; password?: string }
): Promise<UserItem> {
  const { data } = await api.patch<UserItem>(`/users/${id}`, payload)
  return data
}
```

**Step 3: Create UsersPanel component**

```tsx
import { useEffect, useState } from 'react'
import { createUser, getUsers, updateUser } from '../api'
import type { UserItem } from '../types'

interface Props {
  open: boolean
  onClose: () => void
}

export default function UsersPanel({ open, onClose }: Props) {
  const [users, setUsers] = useState<UserItem[]>([])
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState('teacher')
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      getUsers().then(setUsers).catch(() => setError('Не удалось загрузить пользователей'))
    }
  }, [open])

  if (!open) return null

  const handleCreate = async () => {
    setError('')
    try {
      const user = await createUser({ username: newUsername, password: newPassword, role: newRole })
      setUsers([...users, user])
      setNewUsername('')
      setNewPassword('')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка создания')
    }
  }

  const handleToggleActive = async (user: UserItem) => {
    const updated = await updateUser(user.id, { is_active: !user.is_active })
    setUsers(users.map(u => u.id === updated.id ? updated : u))
  }

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ minWidth: 500 }}>
        <h3>Управление пользователями</h3>

        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: 4 }}>Имя</th>
              <th style={{ padding: 4 }}>Роль</th>
              <th style={{ padding: 4 }}>Статус</th>
              <th style={{ padding: 4 }}>Действие</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td style={{ padding: 4 }}>{u.username}</td>
                <td style={{ padding: 4, textAlign: 'center' }}>{u.role}</td>
                <td style={{ padding: 4, textAlign: 'center' }}>
                  {u.is_active ? 'Активен' : 'Заблокирован'}
                </td>
                <td style={{ padding: 4, textAlign: 'center' }}>
                  <button type="button" className="btn ghost" onClick={() => handleToggleActive(u)}>
                    {u.is_active ? 'Блокировать' : 'Активировать'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ marginTop: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
          <input placeholder="Логин" value={newUsername}
            onChange={e => setNewUsername(e.target.value)} style={{ padding: 4 }} />
          <input placeholder="Пароль" type="password" value={newPassword}
            onChange={e => setNewPassword(e.target.value)} style={{ padding: 4 }} />
          <select value={newRole} onChange={e => setNewRole(e.target.value)} style={{ padding: 4 }}>
            <option value="teacher">Учитель</option>
            <option value="admin">Админ</option>
          </select>
          <button type="button" className="btn" onClick={handleCreate}>Добавить</button>
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

**Step 4: Wire into App.tsx**

Add state and render:

```tsx
const [usersOpen, setUsersOpen] = useState(false)

// In TopBar:
onUsersClick={() => setUsersOpen(true)}

// After ImportDialog:
<UsersPanel open={usersOpen} onClose={() => setUsersOpen(false)} />
```

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add user management panel (admin-only)"
```

---

## Task 10: Frontend — Audit log panel (admin)

**Files:**
- Create: `frontend/src/components/AuditPanel.tsx`
- Modify: `frontend/src/api/index.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/App.tsx`

**Step 1: Add types**

Append to `frontend/src/types/index.ts`:

```typescript
export interface AuditLogItem {
  id: number
  username: string
  action: string
  detail: string | null
  created_at: string
}
```

**Step 2: Add API call**

Append to `frontend/src/api/index.ts`:

```typescript
import type { AuditLogItem } from '../types'

export async function getAuditLogs(limit = 50): Promise<AuditLogItem[]> {
  const { data } = await api.get<AuditLogItem[]>(`/audit?limit=${limit}`)
  return data
}
```

**Step 3: Create AuditPanel component**

```tsx
import { useEffect, useState } from 'react'
import { getAuditLogs } from '../api'
import type { AuditLogItem } from '../types'

interface Props {
  open: boolean
  onClose: () => void
}

export default function AuditPanel({ open, onClose }: Props) {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    if (open) {
      getAuditLogs(100)
        .then(setLogs)
        .catch(() => setError('Не удалось загрузить журнал'))
    }
  }, [open])

  if (!open) return null

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ minWidth: 600, maxHeight: '80vh', overflow: 'auto' }}>
        <h3>Журнал действий</h3>

        {error && <div style={{ color: 'red' }}>{error}</div>}

        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12, fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: 4 }}>Время</th>
              <th style={{ textAlign: 'left', padding: 4 }}>Пользователь</th>
              <th style={{ textAlign: 'left', padding: 4 }}>Действие</th>
              <th style={{ textAlign: 'left', padding: 4 }}>Детали</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id}>
                <td style={{ padding: 4, whiteSpace: 'nowrap' }}>
                  {new Date(log.created_at).toLocaleString('ru-RU')}
                </td>
                <td style={{ padding: 4 }}>{log.username}</td>
                <td style={{ padding: 4 }}>{log.action}</td>
                <td style={{ padding: 4, color: '#555' }}>{log.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <button type="button" className="btn ghost" onClick={onClose}>Закрыть</button>
        </div>
      </div>
    </div>
  )
}
```

**Step 4: Wire into App.tsx**

```tsx
const [auditOpen, setAuditOpen] = useState(false)

// In TopBar:
onAuditClick={() => setAuditOpen(true)}

// After UsersPanel:
<AuditPanel open={auditOpen} onClose={() => setAuditOpen(false)} />
```

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add audit log panel (admin-only)"
```

---

## Task 11: Teacher role — restrict to own timetable

**Files:**
- Modify: `backend/app/routers/timetable.py`

**Step 1: Teacher sees only their schedule**

Teachers should be able to view any class/room timetable (they need it for planning), but the teacher list endpoint should work for all. No restriction needed beyond requiring authentication (already in place).

However, **import is already admin-only** (Task 2), and **users/audit are admin-only** (Tasks 3, 7). So the only remaining restriction is:

Teachers cannot export other teachers' timetables? Actually for a school this is fine — teachers should be able to see all schedules. The restriction is on _write_ operations (import, user management), not _read_.

**Decision: No additional timetable restrictions for teachers.** Teachers can view all schedules (read-only). Only admin can import, manage users, and view audit.

This is already implemented by Tasks 2, 3, 7, 8. Mark as complete.

**Step 2: Commit (no code change, update plan only)**

Update progress tracking in plan file.

---

## Task Summary

| # | Task | Scope | Phase |
|---|------|-------|-------|
| 1 | require_role dependency | Backend | P2.2 |
| 2 | Protect import (admin-only) | Backend | P2.2 |
| 3 | User management endpoints | Backend | P2.2 |
| 4 | AuditLog model + migration | Backend | P2.4 |
| 5 | Audit logging service | Backend | P2.4 |
| 6 | Wire audit into endpoints | Backend | P2.4 |
| 7 | Audit log API endpoint | Backend | P2.4 |
| 8 | Role-aware TopBar | Frontend | P2.3 |
| 9 | Users management panel | Frontend | P2.3 |
| 10 | Audit log panel | Frontend | P2.3 |
| 11 | Teacher role restrictions | Decision | P2.2 |
