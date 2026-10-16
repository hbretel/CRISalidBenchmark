"""Qualitative indicators (evaluation grid): per-work sources and answers,
per-journal LLM assessments, institution-level snapshots

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_quality_sources",
        sa.Column("work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("crossref", postgresql.JSONB(), nullable=True),
        sa.Column("hal", postgresql.JSONB(), nullable=True),
        sa.Column("pubmed", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_work_quality_sources_fetched_at", "work_quality_sources", ["fetched_at"])

    op.create_table(
        "work_quality",
        sa.Column("work_id", sa.Text(), sa.ForeignKey("works.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("answers", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("score_base", sa.Float(), nullable=True),
        sa.Column("coefficient", sa.Float(), nullable=True),
        sa.Column("score_final", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_work_quality_coefficient", "work_quality", ["coefficient"])

    op.create_table(
        "journal_quality",
        sa.Column("source_id", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("homepage_url", sa.Text(), nullable=True),
        sa.Column("llm_result", postgresql.JSONB(), nullable=True),
        sa.Column("checked_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "quality_snapshot",
        sa.Column("scope", sa.Text(), primary_key=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("quality_snapshot")
    op.drop_table("journal_quality")
    op.drop_index("ix_work_quality_coefficient", table_name="work_quality")
    op.drop_table("work_quality")
    op.drop_index("ix_work_quality_sources_fetched_at", table_name="work_quality_sources")
    op.drop_table("work_quality_sources")
