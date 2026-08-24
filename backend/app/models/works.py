from datetime import datetime
from sqlalchemy import Text, Integer, Boolean, Float, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Topic(Base):
    """OpenAlex topic taxonomy node.

    OpenAlex organises research topics in a four-level hierarchy:
    Domain > Field > Subfield > Topic (finest granularity, ~4 500 topics).

    This table stores all levels inline to avoid joins for most queries.
    """

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # e.g. "T10175"
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    subfield_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    subfield_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    works: Mapped[list["Work"]] = relationship(back_populates="primary_topic")
    work_topics: Mapped[list["WorkTopic"]] = relationship(back_populates="topic")


class Work(Base):
    """A publication attributed to the configured institution.

    Ingested via filter=institutions.lineage:{id} (not institutions.id) so
    publications from child ROR institutions (components of a federated
    university) are included. See §4.1 of the spec.

    is_core_publication approximates Leiden's "core publication" definition:
    source in CWTS Core list (~36 000 sources) AND article/review/book-chapter
    AND English AND not retracted. This is an approximation — the exact Leiden
    definition additionally applies per-article criteria not exposed by OpenAlex
    without importing a separate ~3 GB classification file.
    """

    __tablename__ = "works"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # OpenAlex ID e.g. "W2741809807"
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    type: Mapped[str | None] = mapped_column(Text, nullable=True)  # article, review, book-chapter…
    cited_by_count: Mapped[int] = mapped_column(Integer, default=0)
    is_oa: Mapped[bool] = mapped_column(Boolean, default=False)
    oa_status: Mapped[str | None] = mapped_column(Text, nullable=True)  # gold/green/hybrid/bronze/closed

    # True if at least one non-institution-country affiliation exists among authorships.
    is_international_collab: Mapped[bool] = mapped_column(Boolean, default=False)

    # Approximation of Leiden "core publication". Used by default when computing
    # scientific impact indicators to maintain methodological coherence with
    # Leiden's pp_top_10 (which is also computed on core publications only).
    is_core_publication: Mapped[bool] = mapped_column(Boolean, default=False)

    primary_topic_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("topics.id", deferrable=True, initially="DEFERRED"), nullable=True
    )
    raw_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )

    primary_topic: Mapped["Topic | None"] = relationship(back_populates="works")
    work_topics: Mapped[list["WorkTopic"]] = relationship(back_populates="work", cascade="all, delete-orphan")


class WorkTopic(Base):
    """M:N association between a work and its OpenAlex topics (scored list).

    OpenAlex returns multiple topics per publication, each with a relevance score.
    primary_topic_id on Work stores the top-ranked topic for convenience; this
    table stores the full scored list for richer disciplinary profile analysis.
    """

    __tablename__ = "work_topics"

    work_id: Mapped[str] = mapped_column(
        Text, ForeignKey("works.id", ondelete="CASCADE"), primary_key=True
    )
    topic_id: Mapped[str] = mapped_column(
        Text, ForeignKey("topics.id"), primary_key=True
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    work: Mapped["Work"] = relationship(back_populates="work_topics")
    topic: Mapped["Topic"] = relationship(back_populates="work_topics")