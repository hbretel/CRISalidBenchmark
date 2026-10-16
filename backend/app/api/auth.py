from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.config import settings
from app.services.auth import (
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    verify_password,
    verify_session_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "crisalid_session"


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    username: str


def _set_session_cookie(response: Response, username: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(username),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
    )


@router.post("/login", response_model=MeResponse)
async def login(body: LoginRequest, response: Response) -> MeResponse:
    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_PASSWORD_HASH is not set — generate one with scripts/hash_password.py.",
        )
    if body.username != settings.ADMIN_USERNAME or not verify_password(
        body.password, settings.ADMIN_PASSWORD_HASH
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides.")

    _set_session_cookie(response, body.username)
    return MeResponse(username=body.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me", response_model=MeResponse)
async def me(request: Request) -> MeResponse:
    token = request.cookies.get(SESSION_COOKIE)
    username = verify_session_token(token) if token else None
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")
    return MeResponse(username=username)
