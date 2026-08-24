import logging
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import config, institution, indicators, peers, profiles, admin
from app.middleware.setup_guard import SetupGuardMiddleware
from app.scheduler import scheduler, setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run DB migrations on startup (development convenience — disable in prod if needed)
    try:
        logger.info("Running Alembic migrations…")
        subprocess.run(["alembic", "upgrade", "head"], check=True, cwd="/app")
        logger.info("Migrations complete")
    except Exception as exc:
        logger.warning("Migration failed (DB may not be ready): %s", exc)

    # Start background scheduler
    setup_scheduler()
    scheduler.start()
    logger.info("APScheduler started")

    yield

    scheduler.shutdown()
    logger.info("APScheduler stopped")


app = FastAPI(
    title="CRISalid Benchmark API",
    version="0.1.0",
    description=(
        "Bibliometric benchmarking tool for academic institutions. "
        "Compares research output against Leiden Ranking peer groups."
    ),
    lifespan=lifespan,
)

# CORS — allow the Next.js dev server and the Docker frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SetupGuardMiddleware)

# Routers
PREFIX = "/api/v1"
app.include_router(config.router, prefix=PREFIX)
app.include_router(institution.router, prefix=PREFIX)
app.include_router(indicators.router, prefix=PREFIX)
app.include_router(peers.router, prefix=PREFIX)
app.include_router(profiles.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
