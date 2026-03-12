from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import export, import_router, timetable

app = FastAPI(title="Ianus", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(import_router.router)
app.include_router(timetable.router)
app.include_router(export.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
