from datetime import datetime
from sqlalchemy import Integer, Text, Float, ForeignKey, UniqueConstraint, CheckConstraint, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PeerGroup(Base):
    """A named set of peer institutions for comparison.

    Three types:
    - geographic: all Leiden institutions sharing the configured institution's
      country_code. Recalculated automatically after each Leiden import.
    - size_bracket: a publication-count decile of the Leiden universe.
      Recalculated automatically after each Leiden import.
    - custom: manually assembled by the user from the Leiden institution list.
    """

    __tablename__ = "peer_groups"
    __table_args__ = (
        CheckConstraint(
            "type IN ('geographic', 'size_bracket', 'custom')",
            name="ck_peer_groups_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    # Null for custom groups (no automatic generation timestamp).
    generated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    # Stores the parameters used to generate predefined groups.
    # e.g. {"country_code": "FR"} or {"decile": 7, "p_min": 500, "p_max": 1200}
    params: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    members: Mapped[list["PeerGroupMember"]] = relationship(
        back_populates="peer_group", cascade="all, delete-orphan"
    )


class PeerGroupMember(Base):
    """Membership of an institution in a peer group.

    Institutions are identified by ror_id (the identifier used in leiden_snapshot).
    """

    __tablename__ = "peer_group_members"

    peer_group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("peer_groups.id", ondelete="CASCADE"), primary_key=True
    )
    ror_id: Mapped[str] = mapped_column(Text, primary_key=True)

    peer_group: Mapped["PeerGroup"] = relationship(back_populates="members")


class PeerTopicCount(Base):
    """Cached per-topic publication statistics, for every institution of the
    peer groups and for the reference institution itself.

    Populated by the peer-cache fill via the OpenAlex group_by API
    (GET /works?filter=authorships.institutions.lineage:{id},publication_year:
    {window}[,extra]&group_by=primary_topic.id), one paginated call per
    statistic: all works, top 10 % cited (citation_normalized_percentile),
    open access, international collaboration (countries_distinct_count > 1).
    These are the topic-level counterparts of the Leiden indicators of the
    impact axis, used by the topics signature (services/topics_signature.py).
    Full publication ingestion for peers stays out of scope (§4.5, option b).

    period_start / period_end: Leiden window the counts cover — rows for
    another window are refetched. The lineage filter is used for peers too
    (same as for the configured institution) so that federated peer
    institutions are not artificially under-counted.
    """

    __tablename__ = "peer_topic_counts"
    __table_args__ = (
        UniqueConstraint(
            "openalex_institution_id", "topic_id",
            name="uq_peer_topic_counts_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openalex_institution_id: Mapped[str] = mapped_column(Text, nullable=False)
    ror_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    topic_id: Mapped[str] = mapped_column(Text, ForeignKey("topics.id"), nullable=False)
    works_count: Mapped[int] = mapped_column(Integer, default=0)
    top10_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oa_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intl_collab_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )


class InstitutionIdMap(Base):
    """Cache resolving ROR IDs to OpenAlex institution IDs.

    leiden_snapshot uses ror_id as the institution identifier (from the Leiden
    dataset). OpenAlex API calls require the OpenAlex ID. This table caches the
    resolution to avoid repeated lookups via GET /institutions/ror:{ror_id}.
    """

    __tablename__ = "institution_id_map"

    ror_id: Mapped[str] = mapped_column(Text, primary_key=True)
    openalex_institution_id: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )