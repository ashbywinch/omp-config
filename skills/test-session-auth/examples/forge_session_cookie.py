"""Forge a session cookie for an app on the itsdangerous timed-serializer
shape (secret + salt + payload). Run after sourcing the app's env, so the
secret is the one the server uses:

    . .env && python <path-to-this-file> > cookie.txt

(no trailing newline is written — read cookie.txt raw)

Env contract:
- SESSION_COOKIE_SECRET  — the server's signing secret (from its env)
- SESSION_COOKIE_PAYLOAD — JSON object: the session identity the app
  stores (email/name/user id — never a literal personal identity)
- SESSION_COOKIE_SALT    — the serializer's salt (omit when the app uses
  none)

A variable set to `None` — how a `.env` file spells an unset value — counts
as absent, so it never becomes the secret or the salt.

An app whose serializer differs (custom salt derivation, non-itsdangerous)
needs its own public serializer — the pattern stays the same.
"""
import json
import os
import sys

from itsdangerous import URLSafeTimedSerializer


def _unset_if_none_spelled(value: str | None) -> str | None:
    """A `.env` file spells an unset variable `None`; treat that as absent, not
    as a value — a secret of "None" signs nothing the server accepts."""
    return None if value is not None and value.strip().lower() == "none" else value


def main() -> None:
    secret = (_unset_if_none_spelled(os.environ.get("SESSION_COOKIE_SECRET")) or "").strip()
    if not secret:
        sys.exit(
            "SESSION_COOKIE_SECRET is required and must not be blank — "
            "set it in the app's env and source it before running."
        )
    try:
        payload = json.loads(os.environ.get("SESSION_COOKIE_PAYLOAD", ""))
    except json.JSONDecodeError as e:
        sys.exit(f"SESSION_COOKIE_PAYLOAD is not valid JSON ({e}) — set the session identity as a JSON object.")
    if not payload or not isinstance(payload, dict):
        sys.exit("SESSION_COOKIE_PAYLOAD must be a non-empty JSON object — the app stores it as the session identity.")
    salt = _unset_if_none_spelled(os.environ.get("SESSION_COOKIE_SALT"))
    if salt is not None and not salt.strip():
        sys.exit("SESSION_COOKIE_SALT is set but blank — set the app's salt or remove the variable.")
    serializer = URLSafeTimedSerializer(secret, salt=salt) if salt else URLSafeTimedSerializer(secret)
    sys.stdout.write(serializer.dumps(payload))


if __name__ == "__main__":
    main()