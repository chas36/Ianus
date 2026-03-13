from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import audit, auth, export, import_router, public, timetable, users

app = FastAPI(title="Ianus", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router.router)
app.include_router(timetable.router)
app.include_router(export.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(public.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
