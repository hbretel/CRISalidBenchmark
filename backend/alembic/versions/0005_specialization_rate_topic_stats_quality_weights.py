"""Specialization rate, per-topic peer statistics, instance-wide quality weights

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16

- Specificity axis: the Herfindahl index and the number of signature topics
  are replaced by a single sub-indicator, the specialization rate in the
  selected Leiden domain (services/indicators_specificity.py). Every profile's
  "specificite_disciplinaire" sub-weights become {"taux_specialisation": 1}.
- Quality axis: the weighting between grid categories (ex-ante / intrinsic /
  ex-post) moves from the weight profiles to the instance ("Paramètres
  d'évaluation qualitative"), stored in instance_config.quality_category_weights.
  The default profile's equal thirds become the instance default; the
  "qualite" sub-weights are dropped from the profiles.
- peer_topic_counts gains the per-topic counts needed by the new topics
  signature (top 10 % cited, open access, international collaboration) and
  the Leiden window they were counted over. Existing rows (all years, volume
  only) are dropped: they are refetched by the next peer-cache fill.
"""

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SPECIFICITY_SUBS = {"taux_specialisation": 1.0}
OLD_SPECIFICITY_SUBS = {"herfindahl": 0.5, "nb_topics_signature": 0.5}
QUALITY_SUBS = {"qualite_ex_ante": 1 / 3, "qualite_intrinseque": 1 / 3, "qualite_ex_post": 1 / 3}


def upgrade() -> None:
    op.add_column("instance_config", sa.Column("quality_category_weights", postgresql.JSONB(), nullable=True))

    op.execute("DELETE FROM peer_topic_counts")
    for column in ("period_start", "period_end", "top10_count", "oa_count", "intl_collab_count"):
        op.add_column("peer_topic_counts", sa.Column(column, sa.Integer(), nullable=True))
    op.create_index("ix_peer_topic_counts_ror_id", "peer_topic_counts", ["ror_id"])

    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, sub_indicator_weights FROM weight_profiles")).all()
    for pid, subs in profiles:
        subs = {k: v for k, v in subs.items() if k != "qualite"}
        subs["specificite_disciplinaire"] = SPECIFICITY_SUBS
        conn.execute(
            sa.text("UPDATE weight_profiles SET sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"s": json.dumps(subs), "id": pid},
        )


def downgrade() -> None:
    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, sub_indicator_weights FROM weight_profiles")).all()
    for pid, subs in profiles:
        subs = {**subs, "specificite_disciplinaire": OLD_SPECIFICITY_SUBS, "qualite": QUALITY_SUBS}
        conn.execute(
            sa.text("UPDATE weight_profiles SET sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"s": json.dumps(subs), "id": pid},
        )
    op.drop_index("ix_peer_topic_counts_ror_id", table_name="peer_topic_counts")
    for column in ("period_start", "period_end", "top10_count", "oa_count", "intl_collab_count"):
        op.drop_column("peer_topic_counts", column)
    op.drop_column("instance_config", "quality_category_weights")
