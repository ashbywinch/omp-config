---
name: google-calendar
description: |
  Google Calendar operations via the `gcalcli` CLI — view schedules, check
  availability, create events, manage the day plan.
---

# Google Calendar

Calendar operations via `gcalcli` — usable from bash commands.

## Prerequisites

- `gcalcli` installed (`~/.local/bin/gcalcli`)
- Authenticated (see Re-authentication below)

Add `~/.local/bin` to PATH if needed.

## Re-authentication

**Symptom**: `gcalcli` fails with `google.auth.exceptions.RefreshError: invalid_grant: Token has been expired or revoked.` — the OAuth token needs refreshing (roughly yearly; re-running auth resets it).

Credentials live in `~/.local/share/gcalcli/oauth` (a pickle of a `google.oauth2.credentials.Credentials`). The Google Cloud client ID/secret are embedded in that pickle (`creds._client_id`, `creds._client_secret`) — recover them from the old file before replacing it. The venv python that has the Google OAuth libs is `~/.local/share/uv/tools/gcalcli/bin/python3`.

**Pick the flow by where the user's browser is:**

### Flow A — user is at the machine (local): `gcalcli init`

```bash
gcalcli init
```
Opens the browser, user clicks through, Google redirects to `localhost:<port>` on the same machine — works. No code pasting. This is the default when the user can reach the laptop's browser.

### Flow B — user is elsewhere (phone/remote): OOB code-paste

gcalcli 4.5 dropped the old copy-paste flow, and its `--noauth_local_server` still requires the browser to reach `localhost:<port>` (fails from a phone; SSH tunnel is the only non-paste route and is NOT worth it). The working route is Google's out-of-band redirect URI with PKCE — the user sees the code on the page, no redirect failure:

1. Generate an auth URL with `redirect_uri=urn:ietf:wg:oauth:2.0:oob`, holding your own PKCE pair (the agent must keep the verifier until the exchange):
   ```python
   # python3 from the gcalcli venv (has google_auth_oauthlib)
   from google_auth_oauthlib.flow import InstalledAppFlow
   client = {"installed": {
       "client_id": "<ID>", "client_secret": "<SECRET>",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]}}
   flow = InstalledAppFlow.from_client_config(client, scopes=["https://www.googleapis.com/auth/calendar"])
   flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
   verifier = secrets.token_urlsafe(48)  # keep this for the exchange
   challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
   url, _ = flow.authorization_url(access_type="offline", prompt="consent",
                                   code_challenge=challenge, code_challenge_method="S256")
   ```
2. Give the user the URL. They authorize on any device; Google displays the code directly on the page — no failed redirect.
3. Exchange with the held verifier and save the credential pickle to `~/.local/share/gcalcli/oauth`:
   ```python
   flow.fetch_token(code="<pasted code>", code_verifier=verifier)
   pickle.dump(flow.credentials, open("~/.local/share/gcalcli/oauth", "wb"))
   ```
4. Verify: `gcalcli agenda` returns without error.

Caveats: never regenerate the flow between steps — the verifier must match the challenge in the URL the user visited. Codes are single-use: if the exchange fails, the user must authorize again with a fresh URL.

### Detecting local vs remote (heuristic, not definitive)

You cannot reliably prove where the user is. Signals to decide Flow A vs B:

| Signal | Local browser likely | Remote/phone likely |
|---|---|---|
| `$DISPLAY`/`$WAYLAND_DISPLAY` set | ✓ | — (display exists but user elsewhere) |
| Browser running: `pgrep -x chrome` etc. | ✓ | — (browser open, nobody watching it) |
| `$SSH_CONNECTION` set (agent is remote) | ✗ | ✓ |
| User says "on my phone"/"on the couch" | ✗ | ✓ |

When signals conflict (e.g. display present but user says phone — the common case), **ask or try Flow A first**: `gcalcli init` fails harmlessly if no local browser reaches it, then fall back to Flow B. Flow B works from anywhere, so when in doubt it is the safe default.

## Before Scheduling

**Always check the current time first:**
```bash
date '+%H:%M'
```
Never schedule events in the past. If a proposed start time has already passed, adjust the plan forward accordingly.

**Never add events without user approval first.** Present the proposed schedule and get explicit confirmation before writing to the calendar.

**REQUIRED: Notion task IDs in every calendar event.** Every work block event MUST include the relevant Notion task ID(s) or epic ID(s) in its description. Never create a work event without a Notion ID — it breaks traceability back to the work items in Notion.

## Rescheduling Flow

When a schedule needs to change (user couldn't start on time, plan shifted):

1. Check current time with `date '+%H:%M'`
2. Present the revised schedule for user approval
3. Once approved, delete the **old** events by search (use specific search text to avoid deleting correct events)
4. Add the new events with task references

## Common Pitfalls

- **Delete is broad**: `gcalcli delete` by search text deletes ALL matching events in the date range. Use specific, unique search terms — not generic words like "Break" or "Lunch" that might hit other days' events.
- **Duration is minutes**: `--duration 90` not `--duration "1:30"`.
- **Calendar name required**: Always pass `--calendar "Home"`. Without it, gcalcli prompts interactively and fails.
- **Task IDs in descriptions**: Every work block needs the Notion task/epic ID so the trace is clear.
- **Check time first**: Never assume what time it is. Run `date`.

## Common Operations

### List calendars
```bash
gcalcli list
```

### View today's agenda
```bash
gcalcli agenda
```

### View a specific date range
```bash
gcalcli agenda "2026-07-28" "2026-07-30"
```

### Quick-add an event
```bash
gcalcli quick "Meeting with team tomorrow 3pm"
```

### Delete events by search
```bash
gcalcli delete --calendar "Home" "Search Text" "2026-07-29" "2026-07-30" --iamaexpert
```
The `--iamaexpert` flag skips the confirmation prompt. Without it, delete is interactive.

### Add a detailed event
```bash
gcalcli add --calendar "Home" --title "Session" \
  --when "2026-07-29 10:00" --duration 120 --noprompt
```
`--duration` takes **minutes** as an integer (e.g. `60` for 1 hour, `30` for 30 minutes).
`--calendar` specifies which calendar to use. Use `gcalcli list` to see available calendars.
`--noprompt` skips interactive prompts for unfilled fields.

### Search for events
```bash
gcalcli search "keyword"
```

## Integration with PA Coordination

The PA Coordination skill uses this for:
- Checking the day plan / schedule
- Adding sessions to the calendar
- Replanning / rescheduling events
- Morning check-in agenda review
