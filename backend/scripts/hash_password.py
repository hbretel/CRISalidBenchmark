"""Generate an ADMIN_PASSWORD_HASH value for .env.

Usage (from the backend/ directory, so `app` is importable):
    python scripts/hash_password.py <password>

Prints the hash to paste into ADMIN_PASSWORD_HASH= in .env. Never store the
plaintext password anywhere — only the printed hash.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.auth import hash_password


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/hash_password.py <password>", file=sys.stderr)
        raise SystemExit(1)
    print(hash_password(sys.argv[1]))


if __name__ == "__main__":
    main()
