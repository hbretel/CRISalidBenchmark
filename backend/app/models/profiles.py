from datetime import datetime
from sqlalchemy import Boolean, Integer, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WeightProfile(Base):
    """A named two-level weighting scheme for the composite benchmark score.

    axis_weights: relative weight of each indicator axis (must sum to 1.0).
      e.g. {"impact_scientifique": 0.6, "specificite_disciplinaire": 0.4}

    sub_indicator_weights: within-axis weights for each sub-indicator (each
      inner dict must sum to 1.0).
      e.g. {
        "impact_scientifique": {
          "impact_normalise_leiden": 0.5,
          "citations_brutes_moyennes": 0.2,
          "oa_pct": 0.15,
          "collab_intl_pct": 0.15
        },
        "specificite_disciplinaire": {
          "herfindahl": 0.7,
          "nb_topics_signature": 0.3
        }
      }

    `impact_normalise_leiden` is an ABSTRACT key, not a literal leiden_snapshot
    column name: indicators_impact.py resolves it to pp_top_10 (core-only toggle)
    or pp_10_cits (all-publications toggle) at calculation time, so a saved
    weight profile stays valid regardless of the toggle state active when it's
    applied (§3.8/§5.1 of the spec — these two columns are not equivalent
    indicators, see indicators_impact.py for the full explanation).

    The composite score is computed on-demand by converting each sub-indicator
    value to a percentile rank within the selected peer group, then applying
    the two-level weighting. No job is scheduled for this — it recalculates
    instantly from data already in the database.

    is_default marks the single seeded "Équilibré" profile (all axes and
    sub-indicators weighted equally) — always present, never deletable or
    editable, used as the fallback comparison profile everywhere in the UI.
    """

    __tablename__ = "weight_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    axis_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sub_indicator_weights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )