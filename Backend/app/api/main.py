from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

WEBAPP_DIR = Path(__file__).resolve().parents[2] / "webapp"

app = FastAPI(title="Zhenya API")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEBAPP_DIR / "index.html")