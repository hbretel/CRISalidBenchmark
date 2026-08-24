"""Admin endpoints for triggering sync jobs manually.

These are intended for operators, not end users. In a production deployment they
should be protected at the reverse-proxy level (e.g. restrict to localhost).
"""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_config
from app.database import get_db
from app.models.instance_config import InstanceConfig
from app.services.leiden_sync import import_leiden_xlsx
from app.services.openalex_sync import run_openalex_sync

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/app/uploads")


@router.post("/sync/openalex")
async def trigger_openalex_sync(
    config: InstanceConfig = Depends(get_config),
) -> dict:
    """Trigger the nightly OpenAlex sync immediately (runs in the background)."""
    asyncio.create_task(run_openalex_sync())
    return {"message": "OpenAlex sync started in the background. Check /sync/status for progress."}


@router.post("/sync/leiden")
async def trigger_leiden_sync(
    snapshot_year: int = Form(...),
    file: UploadFile = File(...),
    config: InstanceConfig = Depends(get_config),
) -> dict:
    """Upload a Leiden Ranking XLSX export and import it.

    The file must be the Leiden Ranking Open Edition export from Zenodo (XLSX).
    Frac_counting=1 rows and all but the most recent Period are skipped (see
    leiden_sync.py for the full filtering logic and column map).

    snapshot_year: the edition year of the ranking (e.g. 2025).
    """
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="File must be an Excel workbook (.xlsx)")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"leiden_{snapshot_year}.xlsx"

    content = await file.read()
    dest.write_bytes(content)
    logger.info("Leiden XLSX uploaded to %s (%d bytes)", dest, len(content))

    # Run import asynchronously
    asyncio.create_task(_run_leiden_import(dest, snapshot_year))

    return {
        "message": f"Leiden XLSX uploaded ({len(content)} bytes). Import started. Check /sync/status."
    }


async def _run_leiden_import(path: Path, snapshot_year: int) -> None:
    try:
        count = await import_leiden_xlsx(path, snapshot_year)
        # Trigger peer group recalculation after successful import
        from app.database import AsyncSessionLocal
        from app.services.peer_groups import recalculate_predefined_groups
        async with AsyncSessionLocal() as session:
            await recalculate_predefined_groups(session)
            await session.commit()
        logger.info("Leiden import complete: %d rows, peer groups recalculated", count)
    except Exception as exc:
        logger.exception("Leiden import failed: %s", exc)


@router.get("/sync/status")
async def sync_status(
    config: InstanceConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import select
    from app.models.sync_log import SyncLog

    result = await session.execute(
        select(SyncLog).order_by(SyncLog.started_at.desc()).limit(10)
    )
    logs = result.scalars().all()
    return {
        "recent_jobs": [
            {
                "id": log.id,
                "job_name": log.job_name,
                "status": log.status,
                "started_at": log.started_at,
                "finished_at": log.finished_at,
                "records_processed": log.records_processed,
                "error_message": log.error_message,
            }
            for log in logs
        ]
    }
