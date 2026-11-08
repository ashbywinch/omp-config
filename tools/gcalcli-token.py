#!/usr/bin/env python3
"""Mint or repair the gcalcli OAuth token without a browser on this machine.

    gcalcli-token.py mint                      print an auth URL; keep the verifier
    gcalcli-token.py exchange '<url-or-code>'  write the credential pickle

The client id and secret are read from the existing pickle when there is one,
otherwise from GCALCLI_CLIENT_ID / GCALCLI_CLIENT_SECRET.

Run it with the interpreter that carries the Google OAuth libraries:

    ~/.local/share/uv/tools/gcalcli/bin/python3 tools/gcalcli-token.py …
"""

import base64
import hashlib
import json
import os
import pathlib
import pickle
import secrets
import sys
import urllib.parse

from google_auth_oauthlib.flow import InstalledAppFlow

# The client block is google_auth_oauthlib's required shape, not a record we own.
# lucidlint: ignore-file record-shape the {"installed": {...}} envelope is the library contract
SCOPES = ["https://www.googleapis.com/auth/calendar"]
FILE_MODE = 0o600
VERIFIER_BYTES = 48
PICKLE = pathlib.Path(os.path.expanduser("~/.local/share/gcalcli/oauth"))
PENDING = pathlib.Path(os.path.expanduser("~/.local/state/gcalcli-oauth-pending.json"))
REDIRECT = "urn:ietf:wg:oauth:2.0:oob"


def client_config():
    """Client credentials: from the existing pickle, else from the environment."""
    if PICKLE.exists():
        try:
            creds = pickle.loads(PICKLE.read_bytes())
        except (pickle.UnpicklingError, EOFError) as exc:  # lucidlint: ignore swallow a corrupt pickle is recoverable: the environment supplies the credentials, and stderr says what happened
            print(f"warning: unreadable credential pickle at {PICKLE}: {exc}", file=sys.stderr)
            creds = None
        client_id = getattr(creds, "_client_id", None)
        client_secret = getattr(creds, "_client_secret", None)
        if client_id and client_secret:
            return client_id, client_secret
    client_id = os.environ.get("GCALCLI_CLIENT_ID")
    client_secret = os.environ.get("GCALCLI_CLIENT_SECRET")
    if not (client_id and client_secret):
        sys.exit("no client credentials: no pickle at %s and no GCALCLI_CLIENT_ID/SECRET" % PICKLE)
    return client_id, client_secret


def mint():
    client_id, client_secret = client_config()
    client = {"installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT],
    }}
    flow = InstalledAppFlow.from_client_config(client, scopes=SCOPES)
    flow.redirect_uri = REDIRECT

    verifier = secrets.token_urlsafe(VERIFIER_BYTES)
    challenge = (base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                 .rstrip(b"=").decode())
    url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                    code_challenge=challenge,
                                    code_challenge_method="S256")

    PENDING.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(PENDING, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    with os.fdopen(fd, "w") as fh:
        json.dump({"verifier": verifier, "client": client}, fh)

    print(url)


def exchange(raw):
    raw = raw.strip()
    if raw.startswith("http"):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        if "error" in query:
            sys.exit("consent refused: " + query["error"][0])
        code = query["code"][0]
    else:
        code = raw

    if not PENDING.exists():
        sys.exit("no pending authorisation: run `mint` first, and use the URL it printed")
    pending = json.loads(PENDING.read_text())

    flow = InstalledAppFlow.from_client_config(pending["client"], scopes=SCOPES)
    flow.redirect_uri = REDIRECT
    flow.fetch_token(code=code, code_verifier=pending["verifier"])

    PICKLE.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(PICKLE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, FILE_MODE)
    with os.fdopen(fd, "wb") as fh:
        pickle.dump(flow.credentials, fh)
    PENDING.unlink()
    print("token written to %s" % PICKLE)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("mint", "exchange"):
        sys.exit(__doc__)
    if sys.argv[1] == "mint":
        mint()
    else:
        if len(sys.argv) < 3:
            sys.exit("exchange needs the callback URL or the code")
        exchange(sys.argv[2])
