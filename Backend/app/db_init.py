import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

log = logging.getLogger(__name__)

ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"


def run_upgrade(revision: str = "head") -> None:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    command.upgrade(config, revision)


async def apply_schema() -> bool:
    try:
        await asyncio.to_thread(run_upgrade)
    except Exception:
        log.exception("Не удалось применить миграции")
        raise
    return True
