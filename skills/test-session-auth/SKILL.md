---
name: test-session-auth
description: Sign into a local app as a test user without a human — forge a session cookie from the server's own secret, or drive the real OAuth flow; never hand the login to the user.
---

# Test-session auth — sign in without a human

## The rule

Never ask the user to log in, and never claim a session-dependent feature
works without exercising it under a real session. Sign in yourself.

## Forge the session cookie (fastest)

The server's own serializer plus its secret produce a cookie the server
accepts as a real session — no browser dance, no provider round-trip. For
apps on the itsdangerous timed-serializer shape, run the sample:
[forge_session_cookie.py](skill://test-session-auth/examples/forge_session_cookie.py).

Invariants (each cost a full session when missed):

- **Source the app's env BEFORE forging** — a different secret silently
  produces an invalid cookie (`authenticated: false` and no error).
- **The identity payload comes from the environment**, never literals —
  no real person's email/name in committed files.
- **Set the cookie scoped to the target URL** (`page.setCookie({name,
  value, url})`) — never `document.cookie` (the harness `run` action
  executes in Node, not the page DOM) and never a bare
  `domain: "localhost"` when the page may open on a LAN address.
- **Non-itsdangerous serializer**: use the app's own public
  serializer/session helper — the forge pattern stays the same.

## Drive the real OAuth flow (when the forge cannot cover it)

Multi-factor, provider-side state, or a server that verifies against the
identity provider: run the real sign-in flow — see `skill://google-auth`
for the authorization-code web flow.

## Then verify the rendered page

A session is the means; the end is looking at the rendered surface.
Screenshot the page and inspect it before claiming the change works —
unit tests and evals test data, not the rendered UI. Never delegate the
visual check to the user.
