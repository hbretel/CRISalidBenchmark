import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


def setup_scheduler() -> None:
    """Register recurring jobs. Called once at application startup."""
    from app.services.openalex_sync import run_openalex_sync
    from app.services.leiden_sync import check_leiden_update

    # Nightly OpenAlex sync at 02:00 UTC.
    scheduler.add_job(
        run_openalex_sync,
        trigger="cron",
        hour=2,
        minute=0,
        id="openalex_nightly",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Monthly check for a new Leiden edition (the import itself is manual).
    scheduler.add_job(
        check_leiden_update,
        trigger="cron",
        day=1,
        hour=6,
        minute=0,
        id="leiden_check_monthly",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info("Scheduled jobs registered: openalex_nightly, leiden_check_monthly")