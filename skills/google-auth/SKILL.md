---
name: google-auth
description: |
  Add Google sign-in to an app — both surfaces: dev apps on a laptop
  accessed from a phone (the OAuth device flow, no redirect URI), and
  production apps on their own domain (the authorization-code web flow).
  One shared session core; most apps grow both.
---

# Google Auth

Sign users in with their Google account. Two deployment shapes, one session
core:

1. **Laptop dev, accessed from the phone** — no domain, no public URL. The
   phone reaches the laptop only by LAN IP, and Google will not take a LAN
   IP as a redirect URI; `localhost` only reaches the laptop's own browser.
   These apps sign in with the **device flow**: a code shown in the app,
   approved at google.com/device on any device, the resulting id_token
   minting the session. No redirect URIs at all.
2. **Production, on its own domain** — the **authorization-code web flow**
   with PKCE: a redirect to Google, back through a registered `https://`
   callback, the code exchanged for a session.

Build the shared core first, then add the flow your deployment needs —
most apps eventually run both behind the same session.

## The shared core (build this once)

- **The session cookie** — a signed, self-contained cookie (e.g.
  itsdangerous's URLSafeTimedSerializer), 30 days, `SameSite=Lax`,
  `Path=/`. The payload is the verified identity: `{email, name, picture}`.
  It survives restarts; nothing is stored server-side per session.
- **`/api/auth/me`** — returns `{authenticated, email, name, picture,
  person}`; `person` is the app's own record for that email, resolved from
  the app's data (the person records carry `email` — the identity mapping
  lives in the DB, never in code or a config file). The app's "who am I"
  everywhere comes from this one endpoint.
- **`/api/auth/logout`** — clears the cookie.
- **Config in the environment** — the OAuth client id/secret and a session
  secret, in the app's env file (gitignored). Secrets are never printed,
  never logged, never in the transcript: check presence with a test, pass
  values by environment, not argv. **A bare launcher (`uv run`, a plain
  exec) does not load the env file — the entrypoint wrapper must source it.**
- **The identity mapping** — the app's people records carry the verified
  Google accounts (`email`); `/me` and the flows resolve the person by
  email (casefolded). An account not in the records is a visitor: they can
  browse, but narrator features and drafts are off.
- **A web-flow id_token is browser-leakable** — it must never mint a
  session at a headless/device endpoint. Each flow verifies against its own
  client id.

## Section 1 — laptop dev app, accessed from the phone (the device flow)

### The Google side (one-time)

Create an OAuth client of type **"TVs and Limited Input devices"** in the
Cloud console (APIs & Services → Credentials → Create credentials → OAuth
client ID). **No redirect URIs, no origins** — that is the point. Copy the
client id and secret into the env.

### The flow

1. `POST /api/auth/device/start` — the server calls Google's
   `https://oauth2.googleapis.com/device/code` with `{client_id, scope:
   openid email profile}`, stores the returned `device_code` in an
   expiring, in-memory state keyed by a random state token, and returns
   `{user_code, verification_url, interval, state}`.
2. The app shows the code and `google.com/device`; the narrator opens it on
   any device, enters the code, approves (2FA if asked). No password flows
   through the app.
3. The app polls `POST /api/auth/device/poll {state}` every `interval`
   seconds. The server exchanges the device code at
   `https://oauth2.googleapis.com/token` and, on approval, verifies the
   returned id_token **bound to the device client** and mints the session
   cookie.

### Device-flow gotchas (each one cost a live failure)

- **Google's device/code and token endpoints answer JSON** — parse JSON,
  never form-encoded.
- **"authorization_pending" arrives as an HTTP 428 whose body is the
  payload** — read error bodies; a non-2xx is not necessarily a failure.
- The device grant's `client_secret` is optional; include it when one is
  configured.
- The in-memory state store: expire it (Google's codes live ~30 min),
  consume it once (replay protection), cap its size.
- The frontend sheet: show the code prominently, link `google.com/device`,
  poll, reload on success, cancel stops the polling. One sheet at a time.

## Section 2 — production app on its own domain (the web flow)

### The Google side (one-time)

Create an OAuth client of type **"Web application"**. Register **exactly**
one redirect URI: `https://<your-domain>/api/auth/callback` — Google
matches it character-for-character. (Console rule of thumb: `https://`
hostnames are fine; raw LAN IPs are not registerable, and plain `http://`
only works for `localhost`.)

### The flow

1. `GET /api/auth/login` — the server builds the Google authorization URL
   (PKCE: a per-login `code_verifier` stored with the state token) and
   returns it; the app redirects the browser there.
2. Google redirects to the registered callback with `code` + `state`. The
   server verifies `state` (consume once, expire), exchanges the code
   (sending the `code_verifier`), verifies the id_token, and **requires
   `email_verified`**.
3. The session cookie is set and the browser redirects to the app.

## Supporting both (the common end-state)

One session core, two flows: the device client + the web client coexist in
the env; both flows end at the same "verify the id_token → mint the cookie"
step. `/me`, the person mapping, and logout are flow-agnostic. A dev app
that grows a production domain keeps the device flow for the LAN and adds
the web client for the domain — the phone works either way.

## Common pitfalls

- **Never try to register a LAN IP as a redirect URI.** Google rejects it;
  `localhost` only reaches the browser on the serving machine. The phone
  path is the device flow, or a real domain.
- **Secrets**: the env file holds the real values; the entrypoint wrapper
  sources it (a bare launcher does not); never print the values — check
  presence, pass by environment, and the transcript stays clean.
- **Verify against the right client.** The device endpoint must verify
  against the device client id, or a browser-leakable web id_token can mint
  sessions anywhere.
- **`email_verified` is required** — an unverified address is not an
  identity.
- **Testing**: the grant state machinery (start/poll/pending/consume) is
  testable with Google stubbed; a real approval is the manual end-to-end
  step. Never hit Google's endpoints from tests.
- **The person mapping is real content** — the family's accounts live on
  the app's person records (append-only supersedes), not in code; unknown
  accounts are visitors until their record carries the email.
