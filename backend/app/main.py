import logging
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, config, institution, indicators, peers, profiles, admin, quality
from app.middleware.auth_guard import AuthGuardMiddleware
from app.middleware.setup_guard import SetupGuardMiddleware
from app.scheduler import scheduler, setup_scheduler

logging.basicConfig(level=logging.INFO)
# httpx logs every request URL at INFO: too noisy for ~10^3-request syncs, and
# a credential passed as a query parameter would end up in the logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
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

    # Instance calibration of the evaluation grid (Paramètres d'évaluation qualitative)
    try:
        await quality.load_grid_overrides()
    except Exception as exc:
        logger.warning("Could not load the grid calibration (DB may not be ready): %s", exc)

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
# Added last so it's outermost and runs first — unauthenticated requests are
# redirected to /login before the setup-guard check ever sees them.
app.add_middleware(AuthGuardMiddleware)

# Routers
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(config.router, prefix=PREFIX)
app.include_router(institution.router, prefix=PREFIX)
app.include_router(indicators.router, prefix=PREFIX)
app.include_router(peers.router, prefix=PREFIX)
app.include_router(profiles.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(quality.router, prefix=PREFIX)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
