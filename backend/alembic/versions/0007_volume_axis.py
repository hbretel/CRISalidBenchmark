"""Volume axis ("Volume de publications") in weight profiles

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-16

New axis of the comparison-group benchmark: the P-type counterparts of the
impact indicators (numbers of publications, services/group_benchmark.py).
  - default "Équilibré" profile: equal weights over the 4 axes;
  - custom profiles: the new axis at 0, so their scores are unchanged.
Every profile gets equal sub-weights over the volume indicators.
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

AXIS = "volume_publications"
VOLUME_KEYS = [
    "p", "p_fwci_1", "p_oa", "p_top_1", "p_cited", "p_top_10", "p_10_cits", "p_int_collab", "p_industry_collab",
]
AXES = ("impact_scientifique", AXIS, "specificite_disciplinaire", "qualite")


def upgrade() -> None:
    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, axis_weights, sub_indicator_weights, is_default FROM weight_profiles")).all()
    for pid, axis, subs, is_default in profiles:
        if AXIS in axis:
            continue
        axis = {k: 1 / len(AXES) for k in AXES} if is_default else {**axis, AXIS: 0.0}
        subs = {**subs, AXIS: {k: 1 / len(VOLUME_KEYS) for k in VOLUME_KEYS}}
        conn.execute(
            sa.text("UPDATE weight_profiles SET axis_weights = CAST(:a AS JSONB), sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"a": json.dumps(axis), "s": json.dumps(subs), "id": pid},
        )


def downgrade() -> None:
    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, axis_weights, sub_indicator_weights FROM weight_profiles")).all()
    for pid, axis, subs in profiles:
        axis = {k: v for k, v in axis.items() if k != AXIS}
        total = sum(axis.values()) or 1.0
        axis = {k: v / total for k, v in axis.items()}
        subs = {k: v for k, v in subs.items() if k != AXIS}
        conn.execute(
            sa.text("UPDATE weight_profiles SET axis_weights = CAST(:a AS JSONB), sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"a": json.dumps(axis), "s": json.dumps(subs), "id": pid},
        )
