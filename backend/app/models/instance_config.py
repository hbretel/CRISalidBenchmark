from datetime import datetime
from sqlalchemy import Integer, Text, CheckConstraint, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class InstanceConfig(Base):
    """Single-row configuration table for the deployed institution.

    Enforced to always have id=1 via a CHECK constraint, making this
    effectively a typed key-value store for instance-level settings.

    The OpenAlex API key is stored here (not in environment variables) so
    it can be entered via the setup wizard and updated without redeployment.
    """

    __tablename__ = "instance_config"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_instance_config_single_row"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    openalex_institution_id: Mapped[str] = mapped_column(Text, nullable=False)
    ror_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    institution_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Stores the full ROR lineage resolved by OpenAlex (list of OpenAlex IDs,
    # self-inclusive). Used as the filter for publication ingestion so that
    # publications affiliated with child institutions (e.g. components of a
    # federated university) are included. Refreshed nightly.
    openalex_lineage_ids: Mapped[dict] = mapped_column(JSONB, default=list, server_default="[]")

    # Stored as plaintext; never returned by any API endpoint.
    # See GET /config which returns api_key_set: bool instead.
    openalex_api_key: Mapped[str] = mapped_column(Text, nullable=False)

    # Used as the `mailto` parameter on OpenAlex calls (secondary identification,
    # complementary to the API key — still recommended by OpenAlex).
    contact_email: Mapped[str] = mapped_column(Text, nullable=False)

    # ISO 3166-1 alpha-2 country code, denormalized from OpenAlex for use in
    # peer group geographic filtering without re-fetching the institution.
    country_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relative weight of the evaluation-grid categories in the benchmark's
    # quality axis ({"qualite_ex_ante": w, "qualite_intrinseque": w,
    # "qualite_ex_post": w}, summing to 1). Edited on the "Paramètres
    # d'évaluation qualitative" page; NULL = equal thirds. See
    # services/quality/comparable.py.
    quality_category_weights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Minimum number of publications for an institution to be compared on a
    # scope (whole institution, OpenAlex domain, topic, Leiden field): below
    # it, its shares are shown but get no percentile, rank or score — shares
    # over a handful of publications are noise. Edited on the Configuration page.
    min_publications: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")

    configured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )