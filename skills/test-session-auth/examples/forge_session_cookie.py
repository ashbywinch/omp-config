"""Forge a session cookie for an app on the itsdangerous timed-serializer
shape (secret + salt + payload). Run after sourcing the app's env, so the
secret is the one the server uses:

    . .env && python <path-to-this-file> > cookie.txt

Env contract:
- SESSION_COOKIE_SECRET  — the server's signing secret (from its env)
- SESSION_COOKIE_PAYLOAD — JSON object: the session identity the app
  stores (email/name/user id — never a literal personal identity)
- SESSION_COOKIE_SALT    — the serializer's salt (omit when the app uses
  none)

An app whose serializer differs (custom salt derivation, non-itsdangerous)
needs its own public serializer — the pattern stays the same.
"""
import json
import os
import sys

from itsdangerous import URLSafeTimedSerializer


def main() -> None:
    try:
        payload = json.loads(os.environ["SESSION_COOKIE_PAYLOAD"])
        secret = os.environ["SESSION_COOKIE_SECRET"]
    except KeyError as e:
        sys.exit(f"{e.args[0]} is required — set SESSION_COOKIE_SECRET and SESSION_COOKIE_PAYLOAD "
                 "in the app's env and source it before running")
    salt = os.environ.get("SESSION_COOKIE_SALT")
    serializer = URLSafeTimedSerializer(secret, salt=salt) if salt else URLSafeTimedSerializer(secret)
    print(serializer.dumps(payload))


if __name__ == "__main__":
    main()
