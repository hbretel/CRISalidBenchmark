"""Per-topic counts of every benchmark criterion

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-16

The topics signature now computes the same four axes as the comparison-group
benchmark (impact, volume, specialization, quality) on each topic, from the
per-topic counts of every criterion (peer_topic_counts.counts, JSONB) instead
of three fixed statistics. Existing rows keep works_count but get counts =
NULL: they are refetched by the next peer-cache fill.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

OLD_COLUMNS = ("top10_count", "oa_count", "intl_collab_count")


def upgrade() -> None:
    op.add_column("peer_topic_counts", sa.Column("counts", postgresql.JSONB(), nullable=True))
    for column in OLD_COLUMNS:
        op.drop_column("peer_topic_counts", column)


def downgrade() -> None:
    for column in OLD_COLUMNS:
        op.add_column("peer_topic_counts", sa.Column(column, sa.Integer(), nullable=True))
    op.drop_column("peer_topic_counts", "counts")
