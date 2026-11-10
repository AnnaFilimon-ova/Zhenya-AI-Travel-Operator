"""Только авиабилеты, индексы под поиск отелей по всему миру, ограничения на корзину.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM cart_tickets WHERE mode <> 'plane'")
    op.execute("UPDATE cart_items SET nights = LEAST(GREATEST(nights, 1), 30)")
    op.execute("ALTER TABLE cart_tickets ADD CONSTRAINT cart_tickets_mode_plane CHECK (mode = 'plane')")
    op.execute("ALTER TABLE cart_items ADD CONSTRAINT cart_items_nights_range CHECK (nights BETWEEN 1 AND 30)")
    op.execute("CREATE INDEX IF NOT EXISTS hotels_city_lower_idx ON hotels (lower(city))")
    op.execute("CREATE INDEX IF NOT EXISTS hotels_geo_idx ON hotels (lat, lon)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hotels_geo_idx")
    op.execute("DROP INDEX IF EXISTS hotels_city_lower_idx")
    op.execute("ALTER TABLE cart_items DROP CONSTRAINT IF EXISTS cart_items_nights_range")
    op.execute("ALTER TABLE cart_tickets DROP CONSTRAINT IF EXISTS cart_tickets_mode_plane")
