"""Create persisted listing records.

Revision ID: 0001
Revises: None
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("zip", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("bedrooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Float(), nullable=False),
        sa.Column("sqft", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("listed_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("source", "id"),
        sa.CheckConstraint("length(source) > 0 AND length(id) > 0", name="ck_listings_identity"),
        sa.CheckConstraint("length(address) > 0", name="ck_listings_address"),
        sa.CheckConstraint("price >= 0", name="ck_listings_price"),
        sa.CheckConstraint("bedrooms >= 0 AND bedrooms = CAST(bedrooms AS INTEGER)", name="ck_listings_bedrooms"),
        sa.CheckConstraint("bathrooms >= 0", name="ck_listings_bathrooms"),
        sa.CheckConstraint("sqft >= 0 AND sqft = CAST(sqft AS INTEGER)", name="ck_listings_sqft"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_listings_latitude"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_listings_longitude"),
        sa.CheckConstraint("status IN ('active', 'pending', 'sold')", name="ck_listings_status"),
    )


def downgrade() -> None:
    op.drop_table("listings")
