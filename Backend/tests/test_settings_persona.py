import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import db_init, settings_store
from app.api import settings_routes
from app.api.auth import current_user


def make_client(monkeypatch, stored=None):
    stored = stored if stored is not None else {}

    async def fake_get(telegram_id):
        return stored.get(telegram_id, "any")

    async def fake_set(tg_user, persona):
        stored[tg_user["id"]] = persona
        return persona

    monkeypatch.setattr(settings_routes, "get_persona", fake_get)
    monkeypatch.setattr(settings_routes, "set_persona", fake_set)
    app = FastAPI()
    app.include_router(settings_routes.router)
    app.dependency_overrides[current_user] = lambda: {"id": 7}
    return TestClient(app), stored


def test_default_then_save_and_read_back(monkeypatch):
    client, stored = make_client(monkeypatch)
    assert client.get("/api/settings").json() == {"persona": "any"}
    assert client.put("/api/settings", json={"persona": "female"}).json() == {"persona": "female"}
    assert stored == {7: "female"}
    assert client.get("/api/settings").json() == {"persona": "female"}


def test_unknown_persona_is_rejected(monkeypatch):
    client, stored = make_client(monkeypatch)
    assert client.put("/api/settings", json={"persona": "robot"}).status_code == 422
    assert client.put("/api/settings", json={}).status_code == 422
    assert stored == {}


def test_store_refuses_unknown_persona_before_touching_database():
    with pytest.raises(ValueError):
        asyncio.run(settings_store.set_persona({"id": 1}, "robot"))
    assert settings_store.PERSONAS == ("female", "male", "any")


def test_instruction_follows_persona():
    pytest.importorskip("google.genai")
    from app.agent import service

    female = service.build_instruction({"persona": "female"}, [])
    male = service.build_instruction({"persona": "male"}, [])
    neutral = service.build_instruction({"persona": "any"}, [])
    missing = service.build_instruction({}, [])
    assert "a woman" in female and "a man" not in female
    assert "a man" in male and "a woman" not in male
    assert "no preference" in neutral and "no preference" in missing
    for text in (female, male, neutral):
        assert "Never change facts" in text and "gender stereotypes" in text


def test_schema_is_applied_on_startup(monkeypatch):
    calls = []
    monkeypatch.setattr(db_init, "run_upgrade", lambda revision="head": calls.append(revision))
    assert asyncio.run(db_init.apply_schema()) is True
    assert calls == ["head"]


def test_startup_fails_loudly_when_migration_breaks(monkeypatch):
    def broken(revision="head"):
        raise OSError("connection refused")

    monkeypatch.setattr(db_init, "run_upgrade", broken)
    with pytest.raises(OSError):
        asyncio.run(db_init.apply_schema())
