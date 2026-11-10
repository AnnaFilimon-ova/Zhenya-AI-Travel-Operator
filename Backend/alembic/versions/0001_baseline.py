"""Начальная схема: повторяет прежний schema.sql, безопасна для уже существующей базы.

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS users (
    id           BIGSERIAL PRIMARY KEY,
    telegram_id  BIGINT NOT NULL UNIQUE,
    username     TEXT,
    first_name   TEXT,
    display_name TEXT,
    gender       TEXT,
    occupation   TEXT,
    language     TEXT NOT NULL DEFAULT 'ru',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE TABLE IF NOT EXISTS user_preferences (
    user_id         BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    with_pets       BOOLEAN NOT NULL DEFAULT FALSE,
    accessible      BOOLEAN NOT NULL DEFAULT FALSE,
    travel_types    TEXT[] NOT NULL DEFAULT '{}',
    food_prefs      TEXT[] NOT NULL DEFAULT '{}',
    favorite_places TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    role        TEXT NOT NULL,
    text        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE INDEX IF NOT EXISTS chat_messages_tg_idx ON chat_messages (telegram_id, id)""",
    """CREATE TABLE IF NOT EXISTS hotels (
    id         BIGSERIAL PRIMARY KEY,
    osm_type   TEXT NOT NULL,
    osm_id     BIGINT NOT NULL,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL,
    city       TEXT NOT NULL,
    address    TEXT,
    lat        DOUBLE PRECISION NOT NULL,
    lon        DOUBLE PRECISION NOT NULL,
    stars      SMALLINT,
    website    TEXT,
    phone      TEXT,
    wheelchair TEXT,
    pets       BOOLEAN,
    tags       JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (osm_type, osm_id)
)""",
    """CREATE INDEX IF NOT EXISTS hotels_city_idx ON hotels (city)""",
    """CREATE TABLE IF NOT EXISTS cart_items (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hotel_id   BIGINT NOT NULL REFERENCES hotels(id) ON DELETE CASCADE,
    nights     SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, hotel_id)
)""",
    """CREATE TABLE IF NOT EXISTS orders (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code        TEXT NOT NULL UNIQUE,
    total       INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'paid',
    provider    TEXT NOT NULL DEFAULT 'demo',
    payment_ref TEXT,
    items       JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE INDEX IF NOT EXISTS orders_user_idx ON orders (user_id, id)""",
    """CREATE TABLE IF NOT EXISTS cart_tickets (
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticket_key   TEXT NOT NULL,
    mode         TEXT NOT NULL,
    origin       TEXT NOT NULL,
    destination  TEXT NOT NULL,
    depart_at    TEXT,
    duration_min INTEGER,
    transfers    SMALLINT,
    car_key      TEXT,
    url          TEXT NOT NULL DEFAULT '',
    price_rub    INTEGER NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, ticket_key)
)""",
    """CREATE TABLE IF NOT EXISTS user_settings (
    user_id    BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    persona    TEXT NOT NULL DEFAULT 'any',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """ALTER TABLE users  ADD COLUMN IF NOT EXISTS occupation  TEXT""",
    """ALTER TABLE orders ADD COLUMN IF NOT EXISTS provider    TEXT NOT NULL DEFAULT 'demo'""",
    """ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_ref TEXT""",
    """UPDATE user_preferences SET travel_types = array_replace(travel_types, 'urbex', 'gothic') WHERE 'urbex' = ANY(travel_types)""",
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Baseline migration cannot be downgraded")
