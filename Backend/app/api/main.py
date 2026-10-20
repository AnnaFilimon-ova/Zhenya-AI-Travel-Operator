from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from app.api.auth import current_user

WEBAPP_DIR = Path(__file__).resolve().parents[2] / "webapp"

app = FastAPI(title="Zhenya API")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return {"id": user["id"], "first_name": user.get("first_name")}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEBAPP_DIR / "index.html")