---
name: google-auth
description: |
  Add Google sign-in to an app — both surfaces: dev apps on a laptop
  accessed from a phone, and production apps on their own domain. The
  authorization-code web flow for both — a LAN app registers a hostname
  that resolves to its IP (sslip.io), never a raw IP or the device flow.
  Build on FastAPI (or your framework) so decoding, cookies, and redirects
  are the framework's job.
---

# Google Auth

Sign users in with their Google account. Two deployment shapes, one flow:

1. **Laptop dev, accessed from the phone** — no domain, a LAN IP. Google
   will not take a raw LAN IP as a redirect URI, and `localhost` only
   reaches the laptop's own browser. The fix is a **hostname that resolves
   to the LAN IP** — `192.168.1.251.sslip.io` (sslip.io's wildcard DNS
   maps the embedded IP to the address) — which Google accepts as a
   redirect URI, so the **normal authorization-code web flow works with no
   code entry and no polling**. (The OAuth device flow is a trap for this
   case: it works, but it costs the user a code + approval dance that the
   hostname flow never needed.)
2. **Production, on its own domain** — the same authorization-code flow
   with a registered `https://<domain>/api/auth/callback`.

Both surfaces use the same code path — only the registered redirect URI
differs. The phone browses the app via the hostname (`http://192.168.1.251.sslip.io:8000`),
so the cookie's host matches the callback's.

## Build on FastAPI (or your framework) — never hand-roll the HTTP

The auth failures come from the plumbing around the OAuth library, not the
library: URL-decoding the callback query (Google percent-encodes the auth
code — `4%2F0AXE…`), parsing the `Cookie` header, reading JSON bodies,
issuing redirects. Use **FastAPI** (or Flask/Django) so those are the
framework's job — `request.query_params` decodes, `request.cookies`
parses, `RedirectResponse`/`JSONResponse` handle the rest (the
framework-owns-parsing rule and its rationale:
`skills/scaffold-language-layers/SKILL.md`). The same reasoning applies
to the frontend: the "Sign in" button fetches the login endpoint and
follows the `auth_url` it returns — navigating straight to the endpoint
renders the JSON as a page.

## The shared core

- **The session cookie** — a signed, self-contained cookie (itsdangerous's
  URLSafeTimedSerializer), 30 days, `HttpOnly`, `SameSite=Lax`, `Path=/`,
  `Secure` when served over HTTPS (the production surface — e.g.
  `secure=not DEBUG`; never on the plain-HTTP LAN flow, where the browser
  would refuse to send it), set by the framework's `set_cookie`. It
  survives restarts.
- **`/api/auth/me`** — `{authenticated, email, name, picture, person}`;
  `person` is the app's own record for that email, resolved from the app's
  data (the person records carry `email` — identity lives in the DB, never
  code or config). The app's "who am I" comes from this one endpoint.
- **The cookie lands on a page navigation, not a fetch response.** The
  phone's network can reject fetch responses carrying a Set-Cookie, and
  mobile browsers race a fetch-set cookie against an immediate reload.
  The proven path: the OAuth callback is a full-page redirect — the
  cookie rides the 302 the browser follows, and the app reloads naturally.
- **Config in the environment** — client id/secret + a session secret in
  the env file (gitignored); the entrypoint wrapper sources it (a bare
  launcher does not — `uv run` doesn't load `.env`). Secrets are never
  printed or logged; check presence, pass by environment. Watch pasted
  env values: a stray space after `=` (`KEY= value`) makes `source` read
  an empty assignment plus a stray command.
- **The identity mapping** — the app's person records carry the verified
  Google accounts; `/me` and the flows resolve the person by email
  (casefolded). An account not in the records is a visitor.

## Section 1 — laptop dev app, accessed from the phone

1. **The Google side**: an OAuth client of type **Web application** with
   one redirect URI: `http://192.168.1.251.sslip.io:8000/api/auth/callback`
   (the LAN IP embedded in the sslip.io hostname + your port). Google
   accepts it — this is the shape a LAN app runs.
2. **The flow**: the login endpoint builds the authorization URL (PKCE,
   state) and sets a short-lived `state` cookie; the app fetches it and
   follows `auth_url`; Google redirects to the registered callback (a
   top-level navigation — the cookie lands there); the callback verifies
   the returned `state` against the cookie and refuses the exchange on
   mismatch; the app's `/me` says authenticated.
3. **Serve the app on the hostname** — the phone browses
   `http://192.168.1.251.sslip.io:8000`, not the raw IP.

## Section 2 — production app on its own domain

The same flow with `https://<your-domain>/api/auth/callback` registered
character-for-character. The consent screen must be configured (app name,
support email); a Testing-mode screen only admits the listed test users.

## Common pitfalls (each one cost a live failure)

- **URL-decode the callback query** — Google percent-encodes the auth
  code; a raw split hands the exchange `4%2F0AXE…` and Google answers
  `(invalid_grant) Malformed auth code`. FastAPI's `request.query_params`
  decodes; a hand-rolled parser does not.
- **Never try to register a raw LAN IP as a redirect URI** — use the
  sslip.io-style hostname; the device flow is a needless detour for
  browsers.
- **The sign-in button follows the login endpoint's `auth_url`** — it
  doesn't navigate to the endpoint directly (and the cookie lands on a
  page navigation, never a fetch response — see the shared core).
- **Verify the `state` parameter in the callback** — it is the login
  flow's CSRF guard; reject a mismatch before exchanging the code.
- **Verify against the right client** — the id_token binds to its OAuth
  client; `email_verified` is required.
- **Log the auth outcomes** (grant started / callback received / session
  minted / `/me` saw a session) at INFO with a visible format — the
  default root logger drops INFO and you diagnose blind.
- **Testing**: exercise the real HTTP stack (the language layer's
  testing rule); stub Google's endpoints — a real approval is the
  manual end-to-end step.
