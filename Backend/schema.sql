CREATE TABLE IF NOT EXISTS users (
    id           BIGSERIAL PRIMARY KEY,
    telegram_id  BIGINT NOT NULL UNIQUE,
    username     TEXT,
    first_name   TEXT,
    display_name TEXT,
    gender       TEXT,
    language     TEXT NOT NULL DEFAULT 'ru',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id         BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    with_pets       BOOLEAN NOT NULL DEFAULT FALSE,
    accessible      BOOLEAN NOT NULL DEFAULT FALSE,
    travel_types    TEXT[] NOT NULL DEFAULT '{}',
    food_prefs      TEXT[] NOT NULL DEFAULT '{}',
    favorite_places TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    role        TEXT NOT NULL,
    text        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS chat_messages_tg_idx ON chat_messages (telegram_id, id);