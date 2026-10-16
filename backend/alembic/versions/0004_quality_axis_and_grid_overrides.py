"""Quality axis in weight profiles, editable grid calibration, peer quality counts

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16

Existing weight profiles get a third axis "qualite":
  - the default "Équilibré" profile is rebalanced to equal thirds (it is
    defined as "all axes weighted equally");
  - custom profiles get qualite = 0, so their composite scores are unchanged
    until the user decides how much weight to give it.
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

QUALITY_SUBS = {"qualite_ex_ante": 1 / 3, "qualite_intrinseque": 1 / 3, "qualite_ex_post": 1 / 3}


def upgrade() -> None:
    op.create_table(
        "quality_grid_overrides",
        sa.Column("criterion_id", sa.Text(), primary_key=True),
        sa.Column("values", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "peer_quality_counts",
        sa.Column("openalex_institution_id", sa.Text(), primary_key=True),
        sa.Column("ror_id", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Integer(), nullable=False),
        sa.Column("counts", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_peer_quality_counts_ror_id", "peer_quality_counts", ["ror_id"])

    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, axis_weights, sub_indicator_weights, is_default FROM weight_profiles")).all()
    for pid, axis, subs, is_default in profiles:
        if "qualite" in axis:
            continue
        if is_default:
            axis = {k: 1 / 3 for k in ("impact_scientifique", "specificite_disciplinaire", "qualite")}
        else:
            axis = {**axis, "qualite": 0.0}
        subs = {**subs, "qualite": QUALITY_SUBS}
        conn.execute(
            sa.text("UPDATE weight_profiles SET axis_weights = CAST(:a AS JSONB), sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"a": json.dumps(axis), "s": json.dumps(subs), "id": pid},
        )


def downgrade() -> None:
    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, axis_weights, sub_indicator_weights, is_default FROM weight_profiles")).all()
    for pid, axis, subs, is_default in profiles:
        axis = {k: v for k, v in axis.items() if k != "qualite"}
        total = sum(axis.values()) or 1.0
        axis = {k: v / total for k, v in axis.items()}
        subs = {k: v for k, v in subs.items() if k != "qualite"}
        conn.execute(
            sa.text("UPDATE weight_profiles SET axis_weights = CAST(:a AS JSONB), sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"a": json.dumps(axis), "s": json.dumps(subs), "id": pid},
        )
    op.drop_index("ix_peer_quality_counts_ror_id", table_name="peer_quality_counts")
    op.drop_table("peer_quality_counts")
    op.drop_table("quality_grid_overrides")
