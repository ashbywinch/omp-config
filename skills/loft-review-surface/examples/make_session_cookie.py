"""Print a valid Loft session cookie for the review surface.

Run from the loft repo root with the main venv's python
(`.venv/bin/python <path-to-this-file>` — NOT .venv-htr; the main venv
has the deps), after sourcing the loft repo's `.env`: the serializer
reads THE_LOFT_SESSION_SECRET from the environment. A different secret
produces an invalid cookie that the server silently rejects
(`authenticated: false`).

The reviewed identity comes from LOFT_REVIEW_EMAIL (required) and
LOFT_REVIEW_NAME (optional) — keep them in the loft repo's gitignored
`.env`, never in this repo.
"""
import os
import sys

sys.path.insert(0, ".")
from tools.auth import _serializer  # noqa: E402

print(_serializer().dumps({
    "email": os.environ["LOFT_REVIEW_EMAIL"],
    "name": os.environ.get("LOFT_REVIEW_NAME", "Review"),
    "picture": "",
}))
