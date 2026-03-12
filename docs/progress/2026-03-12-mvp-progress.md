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
