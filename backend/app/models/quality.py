from datetime import datetime
from sqlalchemy import Text, Float, ForeignKey, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WorkQualitySource(Base):
    """Per-work records fetched from the non-OpenAlex sources of the evaluation
    grid (the OpenAlex record itself is works.raw_json).

    Each column holds only the fields the vendored checkers read, in the shape
    they expect (see app/services/quality/sources.py). NULL means "source not
    reached / not applicable" (no DOI, no PMID, request failed) — distinct from
    an empty result, which the checkers read as a negative answer.
    """

    __tablename__ = "work_quality_sources"

    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), primary_key=True
    )
    crossref: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    hal: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    pubmed: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class WorkQuality(Base):
    """Evaluation-grid answers and score of one work, recomputed on every
    quality run (age criteria depend on the run date).

    answers: {criterion_id: "O" | "N" | "I"} (Oui / Non / Indéterminé), only for
    the criteria the bulk pipeline could reach — evidence is not stored (it is
    rebuilt on demand from the cached sources, see GET /quality/works/{id}).
    score_* are NULL when the grid engine rejected the answer set (error).
    """

    __tablename__ = "work_quality"

    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), primary_key=True
    )
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    score_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class JournalQuality(Base):
    """Per-journal (OpenAlex source) qualitative data that no structured source
    provides: currently the small-LLM reading of the journal's website for
    criterion 1 (peer review) when the journal is absent from DOAJ.

    llm_result: {"verdict", "anonymity", "evidence", "url", "model"} or NULL
    when the journal could not be assessed (no homepage, page unreachable,
    LLM error) — checked_at still records the attempt so it is not retried on
    every run.
    """

    __tablename__ = "journal_quality"

    source_id: Mapped[str] = mapped_column(Text, primary_key=True)  # e.g. "https://openalex.org/S123"
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_result: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class QualitySnapshot(Base):
    """Institution-level aggregates of the last quality run, one row per scope
    ("all" / "core"), so the dashboard never aggregates ~10^5 works × ~150
    criteria at request time."""

    __tablename__ = "quality_snapshot"

    scope: Mapped[str] = mapped_column(Text, primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class QualityGridOverride(Base):
    """Instance-wide calibration of the evaluation grid ("Paramètres
    d'évaluation qualitative" page): one row per criterion whose weight or
    thresholds differ from the vendored default grid.

    values: {"weight": float} and/or {"parameters": {"N": float, "M": float}} —
    see grid.build_effective_grid.
    """

    __tablename__ = "quality_grid_overrides"

    criterion_id: Mapped[str] = mapped_column(Text, primary_key=True)
    values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)


class PeerQualityCount(Base):
    """Per-institution counts of publications meeting each peer-comparable grid
    criterion over a Leiden window (quality axis of the benchmark, see
    services/quality/comparable.py). Includes the reference institution."""

    __tablename__ = "peer_quality_counts"

    openalex_institution_id: Mapped[str] = mapped_column(Text, primary_key=True)
    ror_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    period_start: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[int] = mapped_column(Integer, nullable=False)
    counts: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
