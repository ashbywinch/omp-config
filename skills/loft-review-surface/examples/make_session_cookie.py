"""Print a valid Loft session cookie for the review surface.

Run from the loft repo root with the main venv's python
(`.venv/bin/python <path-to-this-file>` — NOT .venv-htr; the main venv
has the deps, including itsdangerous), after sourcing the loft repo's
`.env`:

    . .env && .venv/bin/python <path-to-this-file>

The secret is read from THE_LOFT_SESSION_SECRET via the auth module's
public `session_secret()`; a different secret produces an invalid cookie
that the server silently rejects (`authenticated: false`). The reviewed
identity comes from LOFT_REVIEW_EMAIL (required) and LOFT_REVIEW_NAME
(optional) — keep them in the loft repo's gitignored `.env`, never in
this repo.
"""
import os
import sys
from dataclasses import asdict, dataclass

from itsdangerous import URLSafeTimedSerializer


# lucidlint: ignore class-module the filename is the example's contract (the skill links to make_session_cookie.py)
@dataclass
class SessionIdentity:
    """The payload the Loft server stores in the session cookie."""

    email: str
    name: str
    picture: str


sys.path.insert(0, ".")
from tools.auth import session_secret  # noqa: E402  (sys.path bootstrap must precede the import)

identity = SessionIdentity(
    email=os.environ["LOFT_REVIEW_EMAIL"],
    name=os.environ.get("LOFT_REVIEW_NAME", "Review"),
    picture="",
)
print(URLSafeTimedSerializer(session_secret(), salt="loft-session").dumps(asdict(identity)))
