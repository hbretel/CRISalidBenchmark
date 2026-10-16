"""Middleware that requires a valid session cookie for all API routes.

Single-admin stand-in until Keycloak is active (see todo.md). Unlike
SetupGuardMiddleware, this needs no DB access — session validity is a pure
signature+expiry check (see services/auth.py) — so there's no "fail open on
DB error" case: a missing/invalid/expired cookie always fails closed.

Added to the app after SetupGuardMiddleware so it becomes outermost and runs
first (Starlette applies middleware in reverse add_middleware order) —
unauthenticated requests are redirected to /login rather than /setup.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.services.auth import verify_session_token

SESSION_COOKIE = "crisalid_session"

EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
}


class AuthGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        if token and verify_session_token(token):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentification requise.", "login_url": "/login"},
            )
        return RedirectResponse(url="/login", status_code=307)
