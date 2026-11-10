"""Домашний город пользователя: откуда лететь по умолчанию.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS home_city TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS chat_messages_created_idx ON chat_messages (created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS chat_messages_created_idx")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS home_city")
