"""OpenAlex-only group benchmark, configurable publication threshold

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16

The comparison-group benchmark no longer uses Leiden data (the "Monde entier"
tab keeps Leiden, without a global score): its impact axis is now made of
OpenAlex counts (services/group_benchmark.py), taken out of the quality axis
where they were double-counted. Profiles' impact sub-weights are remapped:
  - default "Équilibré" profile: equal weights over the new indicators;
  - custom profiles: impact_normalise_leiden → pp_top_10, oa_pct → pp_oa,
    collab_intl_pct → pp_int_collab (citations_brutes_moyennes / h_index_core
    never contributed and are dropped), the other new indicators at 0;
    renormalized to 1 (equal weights if nothing maps).

instance_config.min_publications: minimum number of publications for an
institution to be compared on a scope (domain, topic) — applied everywhere a
percentile or a rank is computed.

Peer quality counts gain a per-OpenAlex-domain breakdown; rows without it are
refetched by the next peer-cache fill (freshness check in comparable.py).
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

IMPACT_KEYS = [
    "pp_top_1", "pp_top_10", "pp_fwci_1", "pp_10_cits", "pp_cited", "pp_oa", "pp_int_collab", "pp_industry_collab",
]
OLD_TO_NEW = {"impact_normalise_leiden": "pp_top_10", "oa_pct": "pp_oa", "collab_intl_pct": "pp_int_collab"}
OLD_DEFAULT_IMPACT = {
    "impact_normalise_leiden": 0.25, "citations_brutes_moyennes": 0.25, "oa_pct": 0.25, "collab_intl_pct": 0.25,
}


def upgrade() -> None:
    op.add_column(
        "instance_config",
        sa.Column("min_publications", sa.Integer(), nullable=False, server_default="10"),
    )

    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, sub_indicator_weights, is_default FROM weight_profiles")).all()
    for pid, subs, is_default in profiles:
        old = subs.get("impact_scientifique", {})
        new = {key: 0.0 for key in IMPACT_KEYS}
        if not is_default:
            for old_key, new_key in OLD_TO_NEW.items():
                new[new_key] += float(old.get(old_key, 0.0))
        total = sum(new.values())
        new = {k: v / total for k, v in new.items()} if total > 0 else {k: 1 / len(IMPACT_KEYS) for k in IMPACT_KEYS}
        subs = {**subs, "impact_scientifique": new}
        conn.execute(
            sa.text("UPDATE weight_profiles SET sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"s": json.dumps(subs), "id": pid},
        )


def downgrade() -> None:
    conn = op.get_bind()
    profiles = conn.execute(sa.text("SELECT id, sub_indicator_weights FROM weight_profiles")).all()
    for pid, subs in profiles:
        subs = {**subs, "impact_scientifique": OLD_DEFAULT_IMPACT}
        conn.execute(
            sa.text("UPDATE weight_profiles SET sub_indicator_weights = CAST(:s AS JSONB) WHERE id = :id"),
            {"s": json.dumps(subs), "id": pid},
        )
    op.drop_column("instance_config", "min_publications")
