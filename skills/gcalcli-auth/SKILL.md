---
name: gcalcli-auth
description: Repair a broken gcalcli Google Calendar token — the two OAuth flows (browser on this machine, browser elsewhere), the credential pickle, and how to tell which flow applies.
---

# gcalcli authentication

Repair only. For scheduling rules and commands, see `skill://google-calendar`.

**Symptom**: `google.auth.exceptions.RefreshError: invalid_grant: Token has been
expired or revoked.` Re-running the auth flow resets it.

Credentials live in `~/.local/share/gcalcli/oauth` — a pickle of a
`google.oauth2.credentials.Credentials`. The Google Cloud client ID and secret
are embedded in that pickle (`creds._client_id`, `creds._client_secret`):
recover them from the old file before replacing it. The venv python carrying the
Google OAuth libraries is `~/.local/share/uv/tools/gcalcli/bin/python3`.

## Pick the flow by where the browser is

You cannot prove where the user is; the signals below are heuristics. When they
conflict — display present but the user says "on my phone", the common case —
ask, or try Flow A first: it fails harmlessly, and Flow B works from anywhere.

| Signal | Local browser likely | Remote/phone likely |
| --- | --- | --- |
| `$DISPLAY` / `$WAYLAND_DISPLAY` set | ✓ | — (display exists, nobody at it) |
| Browser running: `pgrep -x chrome` | ✓ | — |
| `$SSH_CONNECTION` set (agent is remote) | ✗ | ✓ |
| User says "on my phone" / "on the couch" | ✗ | ✓ |

### Flow A — the user is at this machine

```bash
gcalcli init
```

Opens a browser, the user clicks through, Google redirects to
`localhost:<port>` on the same machine. No code pasting.

### Flow B — the user is elsewhere

gcalcli 4.5 dropped the old copy-paste flow, and `--noauth_local_server` still
needs the browser to reach `localhost:<port>` — it fails from a phone, and an SSH
tunnel is not worth it. Use Google's out-of-band redirect with PKCE, so the code
appears on the page instead of in a failed redirect.

1. Generate the URL, keeping your own PKCE pair (the verifier must match the
   challenge in the URL the user visits — never regenerate between steps):

   ```python
   # python3 from the gcalcli venv (it carries google_auth_oauthlib)
   from google_auth_oauthlib.flow import InstalledAppFlow
   client = {"installed": {
       "client_id": "<ID>", "client_secret": "<SECRET>",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]}}
   flow = InstalledAppFlow.from_client_config(client, scopes=["https://www.googleapis.com/auth/calendar"])
   flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
   verifier = secrets.token_urlsafe(48)  # keep for the exchange
   challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
   url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                   code_challenge=challenge, code_challenge_method="S256")
   ```

2. Give the user the URL. They authorise on any device; Google shows the code on
   the page.
3. Exchange it with the held verifier and save the pickle to
   `~/.local/share/gcalcli/oauth`:

   ```python
   flow.fetch_token(code="<pasted code>", code_verifier=verifier)
   pickle.dump(flow.credentials, open("~/.local/share/gcalcli/oauth", "wb"))
   ```

4. Verify: `gcalcli agenda` returns without error.

Codes are single-use. If the exchange fails, the user authorises again with a
fresh URL — never retry a consumed code.
