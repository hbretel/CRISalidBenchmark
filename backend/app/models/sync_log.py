from datetime import datetime
from sqlalchemy import Integer, Text, CheckConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class SyncLog(Base):
    __tablename__ = "sync_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="ck_sync_log_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=datetime.utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="running")
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)