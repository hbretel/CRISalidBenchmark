"""Single-admin auth: password hashing + signed session tokens.

Stand-in until Keycloak is wired up (see todo.md). Deliberately stdlib-only
(hashlib/hmac/base64/json) — no passlib/jose/itsdangerous dependency, since
there's exactly one account and no token revocation/refresh requirements.

Session tokens are self-contained (username + expiry, HMAC-signed with
SECRET_KEY) — verifying one is a pure computation, no DB round-trip. This
mirrors why AuthGuardMiddleware can be simpler than SetupGuardMiddleware
(which has to hit the DB to check whether the instance is configured).

`app.config` (and its pydantic-settings dependency) is imported lazily inside
`_sign()`, not at module level — so `hash_password()` alone (used by
scripts/hash_password.py to generate ADMIN_PASSWORD_HASH) works with a bare
Python stdlib install, without the full backend dependency set.
"""

import base64
import hashlib
import hmac
import json
import time

PBKDF2_ITERATIONS = 260_000
SESSION_MAX_AGE_SECONDS = 7 * 24 * 3600


def hash_password(password: str) -> str:
    salt = hashlib.sha256(str(time.time_ns()).encode() + password.encode()).digest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations_s, salt_hex, digest_hex = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations_s)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


def _sign(payload_b64: str) -> str:
    from app.config import settings

    return hmac.new(settings.SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def create_session_token(username: str) -> str:
    payload = {"username": username, "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{payload_b64}.{_sign(payload_b64)}"


def verify_session_token(token: str) -> str | None:
    """Return the username if the token is validly signed and unexpired, else None."""
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(payload_b64), signature):
        return None

    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except (ValueError, json.JSONDecodeError):
        return None

    if payload.get("exp", 0) < time.time():
        return None

    return payload.get("username")
