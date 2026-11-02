import logging
from pathlib import Path

import asyncpg
from sqlalchemy.engine import make_url

from app.config import settings

log = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema.sql"


async def apply_schema() -> bool:
    try:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        url = make_url(settings.database_url)
        conn = await asyncpg.connect(
            host=url.host, port=url.port, user=url.username,
            password=url.password, database=url.database, timeout=10,
        )
        try:
            await conn.execute(sql) 
        finally:
            await conn.close()
        return True
    except Exception:
        log.exception("Не удалось применить schema.sql")
        return False
