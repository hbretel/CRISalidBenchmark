"""Initial schema — all 12 tables

Revision ID: 0001
Revises:
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── topics ─────────────────────────────────────────────────────────────
    # OpenAlex topic taxonomy (Domain > Field > Subfield > Topic).
    # Stored denormalised to avoid joins; taxonomy changes rarely.
    op.create_table(
        "topics",
        sa.Column("id", sa.Text(), primary_key=True),  # e.g. "T10175"
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("subfield_id", sa.Text(), nullable=True),
        sa.Column("subfield_name", sa.Text(), nullable=True),
        sa.Column("field_id", sa.Text(), nullable=True),
        sa.Column("field_name", sa.Text(), nullable=True),
        sa.Column("domain_id", sa.Text(), nullable=True),
        sa.Column("domain_name", sa.Text(), nullable=True),
    )

    # ── instance_config ────────────────────────────────────────────────────
    # Single-row table (id always = 1). CHECK constraint enforces this.
    op.create_table(
        "instance_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("openalex_institution_id", sa.Text(), nullable=False),
        sa.Column("ror_id", sa.Text(), nullable=True),
        sa.Column("institution_name", sa.Text(), nullable=False),
        # List of OpenAlex institution IDs forming the ROR lineage of the
        # configured institution (self-inclusive). Drives publications filter.
        sa.Column(
            "openalex_lineage_ids",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("openalex_api_key", sa.Text(), nullable=False),
        sa.Column("contact_email", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=True),
        sa.Column(
            "configured_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("id = 1", name="ck_instance_config_single_row"),
    )

    # ── works ──────────────────────────────────────────────────────────────
    op.create_table(
        "works",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("cited_by_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_oa", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("oa_status", sa.Text(), nullable=True),
        sa.Column("is_international_collab", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_core_publication", sa.Boolean(), nullable=False, server_default="false"),
        # FK deferrable: topics upsert and works upsert run in same transaction;
        # topics may be processed after the work referencing them.
        sa.Column(
            "primary_topic_id",
            sa.Text(),
            sa.ForeignKey("topics.id", deferrable=True, initially="DEFERRED"),
            nullable=True,
        ),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "last_synced_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── work_topics ────────────────────────────────────────────────────────
    op.create_table(
        "work_topics",
        sa.Column("work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE")),
        sa.Column("topic_id", sa.Text(), sa.ForeignKey("topics.id")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("work_id", "topic_id"),
    )

    # ── leiden_snapshot ────────────────────────────────────────────────────
    # Up to 12 rows per (institution, snapshot_year): field='All sciences' or
    # one of 5 Leiden macro-domains, × core_pubs_only in {True, False}.
    # frac_counting is always False in the MVP (fractional counting deferred
    # to v2) but kept as a real column so v2 rows require no migration.
    op.create_table(
        "leiden_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ror_id", sa.Text(), nullable=False),
        sa.Column("university_name", sa.Text(), nullable=True),
        sa.Column("country_code", sa.Text(), nullable=True),
        sa.Column("snapshot_year", sa.Integer(), nullable=False),
        sa.Column("period", sa.Text(), nullable=True),
        sa.Column("field", sa.Text(), nullable=False, server_default="All sciences"),
        sa.Column("core_pubs_only", sa.Boolean(), nullable=False),
        sa.Column("frac_counting", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("p", sa.Numeric(), nullable=True),
        sa.Column("tcs", sa.Float(), nullable=True),
        sa.Column("mcs", sa.Float(), nullable=True),
        sa.Column("mcs_lb", sa.Float(), nullable=True),
        sa.Column("mcs_ub", sa.Float(), nullable=True),
        sa.Column("mncs", sa.Float(), nullable=True),
        sa.Column("mncs_lb", sa.Float(), nullable=True),
        sa.Column("mncs_ub", sa.Float(), nullable=True),
        sa.Column("pp_top_1", sa.Float(), nullable=True),
        sa.Column("pp_top_1_lb", sa.Float(), nullable=True),
        sa.Column("pp_top_1_ub", sa.Float(), nullable=True),
        sa.Column("pp_top_5", sa.Float(), nullable=True),
        sa.Column("pp_top_5_lb", sa.Float(), nullable=True),
        sa.Column("pp_top_5_ub", sa.Float(), nullable=True),
        sa.Column("pp_top_10", sa.Float(), nullable=True),
        sa.Column("pp_top_10_lb", sa.Float(), nullable=True),
        sa.Column("pp_top_10_ub", sa.Float(), nullable=True),
        sa.Column("pp_top_50", sa.Float(), nullable=True),
        sa.Column("pp_top_50_lb", sa.Float(), nullable=True),
        sa.Column("pp_top_50_ub", sa.Float(), nullable=True),
        sa.Column("pp_10_cits", sa.Float(), nullable=True),
        sa.Column("pp_10_cits_lb", sa.Float(), nullable=True),
        sa.Column("pp_10_cits_ub", sa.Float(), nullable=True),
        sa.Column("pp_20_cits", sa.Float(), nullable=True),
        sa.Column("pp_20_cits_lb", sa.Float(), nullable=True),
        sa.Column("pp_20_cits_ub", sa.Float(), nullable=True),
        sa.Column("pp_50_cits", sa.Float(), nullable=True),
        sa.Column("pp_50_cits_lb", sa.Float(), nullable=True),
        sa.Column("pp_50_cits_ub", sa.Float(), nullable=True),
        sa.Column("pp_100_cits", sa.Float(), nullable=True),
        sa.Column("pp_100_cits_lb", sa.Float(), nullable=True),
        sa.Column("pp_100_cits_ub", sa.Float(), nullable=True),
        sa.Column("pp_int_collab", sa.Float(), nullable=True),
        sa.Column("pp_int_collab_lb", sa.Float(), nullable=True),
        sa.Column("pp_int_collab_ub", sa.Float(), nullable=True),
        sa.Column("pp_oa", sa.Float(), nullable=True),
        sa.Column("pp_oa_lb", sa.Float(), nullable=True),
        sa.Column("pp_oa_ub", sa.Float(), nullable=True),
        sa.Column("raw_row", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint(
            "ror_id", "field", "period", "core_pubs_only", "snapshot_year",
            name="uq_leiden_snapshot_key",
        ),
    )

    # ── peer_groups ────────────────────────────────────────────────────────
    op.create_table(
        "peer_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.CheckConstraint(
            "type IN ('geographic', 'size_bracket', 'custom')",
            name="ck_peer_groups_type",
        ),
    )

    # ── peer_group_members ─────────────────────────────────────────────────
    op.create_table(
        "peer_group_members",
        sa.Column(
            "peer_group_id",
            sa.Integer(),
            sa.ForeignKey("peer_groups.id", ondelete="CASCADE"),
        ),
        sa.Column("ror_id", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("peer_group_id", "ror_id"),
    )

    # ── peer_topic_counts ──────────────────────────────────────────────────
    # On-demand cache: publication counts per topic for peer institutions.
    # Populated via group_by API call (cheap). Volume-only — no citation data.
    op.create_table(
        "peer_topic_counts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("openalex_institution_id", sa.Text(), nullable=False),
        sa.Column("ror_id", sa.Text(), nullable=True),
        sa.Column("topic_id", sa.Text(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("works_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "fetched_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "openalex_institution_id", "topic_id",
            name="uq_peer_topic_counts_key",
        ),
    )

    # ── institution_id_map ─────────────────────────────────────────────────
    # ROR → OpenAlex ID resolution cache (peers are identified by ROR in
    # leiden_snapshot; OpenAlex API calls need the OpenAlex ID).
    op.create_table(
        "institution_id_map",
        sa.Column("ror_id", sa.Text(), primary_key=True),
        sa.Column("openalex_institution_id", sa.Text(), nullable=False),
        sa.Column(
            "resolved_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── weight_profiles ────────────────────────────────────────────────────
    op.create_table(
        "weight_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("axis_weights", postgresql.JSONB(), nullable=False),
        sa.Column("sub_indicator_weights", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── benchmark_views ────────────────────────────────────────────────────
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
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── sync_log ───────────────────────────────────────────────────────────
    op.create_table(
        "sync_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_name", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="ck_sync_log_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("sync_log")
    op.drop_table("benchmark_views")
    op.drop_table("weight_profiles")
    op.drop_table("institution_id_map")
    op.drop_table("peer_topic_counts")
    op.drop_table("peer_group_members")
    op.drop_table("peer_groups")
    op.drop_table("leiden_snapshot")
    op.drop_table("work_topics")
    op.drop_table("works")
    op.drop_table("instance_config")
    op.drop_table("topics")