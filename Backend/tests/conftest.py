import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest 

from app.providers import registry 


@pytest.fixture(autouse=True)
def _clean_registry():
    yield
    registry.reset()
