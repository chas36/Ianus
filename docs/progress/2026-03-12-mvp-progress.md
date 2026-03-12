# MVP Progress Log (2026-03-12)

## What Was Implemented

1. Infra baseline:
- Added `.gitignore`
- Added `.env.example`
- Added `docker-compose.yml` with PostgreSQL 16

2. Backend baseline:
- Added `backend/requirements.txt`
- Added FastAPI app entrypoint (`backend/app/main.py`)
- Added settings and async DB session setup (`backend/app/config.py`, `backend/app/database.py`)

3. Data layer:
- Added ORM models for imports, dictionaries, lessons, and cards (`backend/app/models.py`)
- Initialized Alembic and added initial migration (`backend/alembic/*`)

4. Parsing:
- Added aSc XML parser service (`backend/app/services/asc_xml_parser.py`)
- Added parser tests (`backend/tests/test_asc_xml_parser.py`)

5. API contracts and endpoints:
- Added Pydantic schemas (`backend/app/schemas.py`)
- Added XML import endpoint (`backend/app/routers/import_router.py`)
- Added timetable endpoints (`backend/app/routers/timetable.py`)
- Registered routers in `backend/app/main.py`

## Verification Results

- Parser tests: `9 passed`
- Python compile check for backend modules: passed
- FastAPI health endpoint from backend cwd (`uvicorn app.main:app`): `{"status":"ok"}`
- Alembic offline SQL generation (`alembic upgrade head --sql`): passed

## Known Blockers

- Docker daemon is not running locally, so these checks are pending:
  - `docker compose up -d db`
  - live `psql` connectivity check
  - real `alembic upgrade head` against running PostgreSQL
  - runtime verification of import/timetable endpoints with actual DB data

## Next Slice

1. Start PostgreSQL and run DB migration online.
2. Import `export_file/import.xml` through API.
3. Implement export service (Task 9).
4. Move to frontend tasks (10+).

---

## Update (2026-03-12, continuation)

### Completed in this pass

1. Export backend (Task 9):
- Added XLSX generation service: `backend/app/services/export_service.py`
- Added PDF HTML generation and WeasyPrint render path
- Added export routes for class/teacher/room: `backend/app/routers/export.py`
- Registered export router in `backend/app/main.py`

2. Frontend MVP UI (Task 10-16):
- Initialized Vite React+TS app in `frontend/`
- Added API client and shared types (`frontend/src/api`, `frontend/src/types`)
- Added components: `TopBar`, `Sidebar`, `TimetableGrid`, `ImportDialog`
- Wired full screen app in `frontend/src/App.tsx`
- Added visual theme and responsive layout in `frontend/src/App.css` and `frontend/src/index.css`
- Configured Vite proxy to backend in `frontend/vite.config.ts`

### Verification

- Frontend production build: `npm run build` — passed
- Backend parser tests: `9 passed`
- Backend compile check: passed

### Remaining runtime checks

- Requires running local PostgreSQL container and online migration/import checks.
- Requires manual UI smoke test against running backend + DB:
  - import XML,
  - open timetable for entity,
  - export XLSX/PDF.

---

## Runtime Smoke Test (2026-03-12)

### Environment bring-up

- Docker Desktop started successfully.
- PostgreSQL started: `docker compose up -d db`
- DB readiness check passed (`SELECT 1`).
- Alembic migration applied online: `alembic upgrade head`.

### API smoke results

- `GET /api/health` -> `200`, body: `{"status":"ok"}`
- `POST /api/import/asc-xml` with `export_file/import.xml` -> `200`, body:
  `{"subjects":102,"teachers":71,"classes":51,"rooms":78,"lessons":679,"cards":1644}`
- Entity lists:
  - classes: 51
  - teachers: 71
  - rooms: 78
- Timetable endpoints (`class/teacher/room`) return 10 rows with non-empty cells.

### Export smoke results

- `GET /api/export/class/{id}?format=xlsx` -> `200`, file generated (`6259` bytes)
- `GET /api/export/class/{id}?format=pdf` -> `503`, reason:
  missing WeasyPrint system dependencies in host environment (`pango/cairo/gobject`)

Implemented mitigation in API:
- XLSX works with ASCII-safe filenames in `Content-Disposition`.
- PDF failure now returns explicit `503` with actionable detail instead of raw `500`.

### Frontend smoke

- Vite dev server starts on `http://127.0.0.1:5173`.
- Root HTML response received successfully.

---

## UI Iteration (2026-03-12)

- Frontend timetable grid orientation changed:
  - Y-axis: weekdays
  - X-axis: periods and time
- Improved readability and status visibility:
  - selected mode/entity line in header
  - compact info chips in content header
  - improved cell/card styling for dense timetable view

---

## PDF Export Closure (2026-03-12)

- Installed WeasyPrint host dependencies on macOS via Homebrew (`glib`, `pango`, `gdk-pixbuf`, `cairo`, `libffi`).
- Added backend runtime preparation for WeasyPrint on macOS:
  - sets `DYLD_FALLBACK_LIBRARY_PATH` to include `/opt/homebrew/lib` when available.
- Re-ran export smoke:
  - XLSX: `200` (`6259` bytes)
  - PDF: `200` (`18081` bytes)

Result: Task 9 fully validated in runtime (both formats).
