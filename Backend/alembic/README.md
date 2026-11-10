# Миграции базы

Миграции применяются автоматически при старте API (`docker compose up`). Вручную, из папки `Backend`:

    alembic upgrade head          # применить всё
    alembic current               # текущая версия базы
    alembic downgrade -1          # откатить последнюю миграцию (кроме 0001)

Новая миграция пишется вручную:

    alembic revision -m "что меняем" --rev-id 0003

В файле заполни `upgrade()` и `downgrade()` через `op.execute("...")` и положи его в `alembic/versions/`.
`--autogenerate` не использовать: часть таблиц (`cart_tickets`, `user_settings`) создаётся SQL, а не моделями.

Миграция 0001 повторяет прежний `schema.sql` через `IF NOT EXISTS`, поэтому безопасна и для пустой базы,
и для уже работающей. `stamp` не нужен.
