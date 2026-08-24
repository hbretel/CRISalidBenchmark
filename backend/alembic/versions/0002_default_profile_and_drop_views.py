"""Add default "Équilibré" weight profile, drop benchmark_views

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Equal weights across both axes, and equal weights across each axis's
# sub-indicators — this is what "Équilibré" (balanced) means. Kept in sync
# with the sub-indicator keys used by indicators_impact.py / indicators_specificity.py.
DEFAULT_AXIS_WEIGHTS = {
    "impact_scientifique": 0.5,
    "specificite_disciplinaire": 0.5,
}
DEFAULT_SUB_WEIGHTS = {
    "impact_scientifique": {
        "impact_normalise_leiden": 0.25,
        "citations_brutes_moyennes": 0.25,
        "oa_pct": 0.25,
        "collab_intl_pct": 0.25,
    },
    "specificite_disciplinaire": {
        "herfindahl": 0.5,
        "nb_topics_signature": 0.5,
    },
}


def upgrade() -> None:
    op.add_column(
        "weight_profiles",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
    )

    weight_profiles = sa.table(
        "weight_profiles",
        sa.column("name", sa.Text()),
        sa.column("axis_weights", postgresql.JSONB()),
        sa.column("sub_indicator_weights", postgresql.JSONB()),
        sa.column("is_default", sa.Boolean()),
    )
    op.bulk_insert(
        weight_profiles,
        [
            {
                "name": "Équilibré",
                "axis_weights": DEFAULT_AXIS_WEIGHTS,
                "sub_indicator_weights": DEFAULT_SUB_WEIGHTS,
                "is_default": True,
            }
        ],
    )

    op.drop_table("benchmark_views")


def downgrade() -> None:
    op.create_table(
        "benchmark_views",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "weight_profile_id",
            sa.Integer(),
            sa.ForeignKey("weight_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "peer_group_id",
            sa.Integer(),
            sa.ForeignKey("peer_groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.execute("DELETE FROM weight_profiles WHERE is_default = true")
    op.drop_column("weight_profiles", "is_default")
