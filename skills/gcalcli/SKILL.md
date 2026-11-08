---
name: gcalcli
description: Drive Google Calendar from the gcalcli command line — adding, searching, listing and deleting events, the flags that hang or over-delete, and how to mint a new OAuth token when the old one expires.
---

# gcalcli

The command-line calendar tool, its commands, its traps, and its token.

## Commands

`gcalcli` needs `--calendar` on writes: without it the command prompts
interactively and fails, because an agent cannot answer a prompt.

```bash
gcalcli list                                  # calendars available
gcalcli agenda                                # today
gcalcli agenda "2026-11-07" "2026-11-08"      # a range
gcalcli search "keyword"                      # find an event

gcalcli quick "Dentist Tuesday 3pm"           # natural-language quick add
gcalcli add --calendar "Home" --title "Session" \
  --when "2026-11-07 10:00" --duration 45 --noprompt
gcalcli delete --calendar "Home" "unique text" "2026-11-07" "2026-11-08" --iamaexpert
```

## Traps

- **`delete` is a shotgun**: it deletes *every* match in the date range. Use
  unique search text, a narrow range, and never a word like "Break" or "Lunch".
- **`delete` prompts** unless you pass `--iamaexpert`; an unprompted agent hangs
  waiting for an answer that never comes.
- **`--duration` is minutes**: `--duration 90`, never `"1:30"`.
- **`--calendar` is required on writes**, and the name must exist — check
  `gcalcli list` first when the account has more than one.

## When the token expires

Symptom: `google.auth.exceptions.RefreshError: invalid_grant: Token has been
expired or revoked`.

The credential is a pickle at `~/.local/share/gcalcli/oauth` holding a
`google.oauth2.credentials.Credentials` — the client id and secret live inside
it (`creds._client_id`, `creds._client_secret`), so recover them from the old
file before replacing it.

If the user is at this machine, `gcalcli init` opens a browser and is the
shortest path. If they are elsewhere — a phone, another machine — use the
out-of-band flow: Google shows the code on the page instead of redirecting to a
`localhost` port nobody is listening on.

**Run the script with the interpreter that carries the OAuth libraries**:
`~/.local/share/uv/tools/gcalcli/bin/python3`.

```bash
python3 gcalcli-token.py mint
# give the printed URL to the user; they authorise anywhere and paste the code back
python3 gcalcli-token.py exchange "<url-or-code>"
gcalcli agenda                                 # verify
```

`mint` keeps the PKCE verifier, so the URL must be the one it printed — never
regenerate between the two steps. Codes are single-use: a failed exchange needs
a fresh `mint`.

## Which of this and the MCP tools

Both write the same calendar. `gcalcli` is a local binary with its own token; the
MCP tools ride on the workspace's Google grant, and `skill://google-calendar` says
which to use. The rules for *whether* and *when* to write live there too.
