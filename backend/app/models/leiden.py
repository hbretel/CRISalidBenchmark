from sqlalchemy import Integer, Text, Float, Numeric, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class LeidenSnapshot(Base):
    """Annual Leiden Ranking Open Edition import (schema per spec v1.7).

    Source file: XLSX export from Zenodo, long/tidy format — one row per
    (institution, field, period, Core_pubs_only, Frac_counting) combination.
    The MVP imports only the most recent `period` and only `frac_counting=False`
    rows (fractional counting deferred to v2), but keeps **both** values of
    `core_pubs_only`:
      - core_pubs_only=True  : Leiden's "core publications" subset — exposes the
        field-normalised percentile family (pp_top_1/5/10/50, mncs).
      - core_pubs_only=False : the full corpus — exposes a different, NON
        field-normalised family based on absolute citation thresholds
        (pp_10/20/50/100_cits). These two families are NOT equivalent
        indicators; pp_top_10 and pp_10_cits must never be presented as the
        same figure under a transparent toggle (see indicators_impact.py).

    `field` takes exactly 6 values: "All sciences" (whole-institution) plus the
    5 Leiden macro-domains (Biomedical and health sciences, Life and earth
    sciences, Mathematics and computer science, Physical sciences and
    engineering, Social sciences and humanities).

    `p` is numeric (not integer) because per-domain rows split interdisciplinary
    publications fractionally across the 5 domains — independent of
    `frac_counting`, which concerns co-authorship sharing between institutions.
    On `field='All sciences'` rows, `p` is always a whole number.
    """

    __tablename__ = "leiden_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "ror_id", "field", "period", "core_pubs_only", "snapshot_year",
            name="uq_leiden_snapshot_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Normalized: stored WITHOUT the "https://ror.org/" prefix. Must be
    # stripped the same way wherever a ROR from OpenAlex (full URI) is compared.
    ror_id: Mapped[str] = mapped_column(Text, nullable=False)
    university_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ISO 3166-1 alpha-2, resolved at import time from the source file's plain
    # country name (e.g. "Pakistan") via a name→ISO2 mapping table.
    country_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    snapshot_year: Mapped[int] = mapped_column(Integer, nullable=False)

    # 4-year rolling window, e.g. "2020–2023" (en dash, U+2013). Only the most
    # recent period present in the source file is imported.
    period: Mapped[str | None] = mapped_column(Text, nullable=True)

    # "All sciences" or one of the 5 Leiden macro-domains.
    field: Mapped[str] = mapped_column(Text, nullable=False, default="All sciences")

    # Row dimensions from the source file (Core_pubs_only / Frac_counting).
    core_pubs_only: Mapped[bool] = mapped_column(Boolean, nullable=False)
    frac_counting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Number of publications on this row's field scope. Numeric, not int — see
    # docstring above. Guaranteed integer on field='All sciences' rows.
    p: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    # Total citations, non field-normalised. Empty only when p=0.
    tcs: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Mean citations per publication, non field-normalised. Available on both
    # core_pubs_only values (unlike mncs below).
    mcs: Mapped[float | None] = mapped_column(Float, nullable=True)
    mcs_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    mcs_ub: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Mean citations, field-normalised (1.0 = world field average). Only
    # populated on core_pubs_only=True rows — NULL otherwise, because field
    # normalisation requires the "core" journal classification.
    mncs: Mapped[float | None] = mapped_column(Float, nullable=True)
    mncs_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    mncs_ub: Mapped[float | None] = mapped_column(Float, nullable=True)

    # % publications in the top 1/5/10/50% most cited, field-normalised.
    # Proportions 0-1 (×100 only at display time). Only populated on
    # core_pubs_only=True rows — NULL on core_pubs_only=False rows.
    pp_top_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_1_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_1_ub: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_5_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_5_ub: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_10: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_10_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_10_ub: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_50: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_50_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_top_50_ub: Mapped[float | None] = mapped_column(Float, nullable=True)

    # % publications with at least N citations — absolute threshold, NOT
    # field-normalised. Only populated on core_pubs_only=False rows — exactly
    # the inverse availability of the pp_top_* family above. pp_10_cits is the
    # headline indicator used in place of pp_top_10 when the impact-scientifique
    # toggle is set to "all publications" (see §5.1/§7 of the spec) — the two
    # are NOT equivalent (percentile-normalised-by-field vs raw citation floor).
    pp_10_cits: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_10_cits_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_10_cits_ub: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_20_cits: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_20_cits_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_20_cits_ub: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_50_cits: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_50_cits_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_50_cits_ub: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_100_cits: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_100_cits_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_100_cits_ub: Mapped[float | None] = mapped_column(Float, nullable=True)

    # % publications in international collaboration. Present regardless of
    # core_pubs_only (empty only if frac_counting=1, not imported in MVP).
    pp_int_collab: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_int_collab_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_int_collab_ub: Mapped[float | None] = mapped_column(Float, nullable=True)

    # % publications open access. Same availability as pp_int_collab.
    pp_oa: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_oa_lb: Mapped[float | None] = mapped_column(Float, nullable=True)
    pp_oa_ub: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Full source row (~88 columns) — preserves fields not promoted above
    # (P_top_*, P_industry_collab, PP_industry_collab, per-OA-type columns…)
    # so they can be promoted in v2 without a re-import.
    raw_row: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
