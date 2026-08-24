"""Middleware that redirects all non-config routes to /setup if unconfigured.

Uses a module-level flag cached after first confirmed configuration to avoid a
DB round-trip on every request once the instance is configured.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

_configured: bool = False

EXEMPT_PATHS = {
    "/api/v1/config",
    "/api/v1/config/validate",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
}


class SetupGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _configured

        # Once confirmed configured, skip the guard entirely
        if _configured:
            return await call_next(request)

        path = request.url.path

        # Exempt setup and docs routes
        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return await call_next(request)

        # Check DB
        try:
            from app.database import AsyncSessionLocal
            from app.models.instance_config import InstanceConfig
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(InstanceConfig.id).where(InstanceConfig.id == 1)
                )
                exists = result.scalar_one_or_none() is not None

            if exists:
                _configured = True
                return await call_next(request)
        except Exception:
            pass

        # Not configured — return 503 for API routes, redirect for browser routes
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Instance not yet configured. Complete setup at /setup.",
                    "setup_url": "/setup",
                },
            )
        return RedirectResponse(url="/setup", status_code=307)
