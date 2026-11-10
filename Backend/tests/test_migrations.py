from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]


def script() -> ScriptDirectory:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def test_single_linear_history():
    directory = script()
    assert directory.get_heads() == ["0003"]
    chain = [rev.revision for rev in directory.walk_revisions()]
    assert chain == ["0003", "0002", "0001"]


def test_baseline_creates_every_table():
    text = (ROOT / "alembic" / "versions" / "0001_baseline.py").read_text(encoding="utf-8")
    for table in ("users", "user_preferences", "chat_messages", "hotels", "cart_items", "orders", "cart_tickets", "user_settings"):
        assert f"CREATE TABLE IF NOT EXISTS {table} " in text, table
