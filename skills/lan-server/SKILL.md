---
name: lan-server
description: |
  Launching a project's long-running server through the hub (supervised).
  User-facing servers MUST be started with persist: true and a ready
  condition — the hub tears down non-persistent processes when the last
  omp session ends, and the server dies silently mid-use (2026-08-16: the
  loft-serve died under the user mid-review; the logs showed a clean
  SIGTERM, no crash). Carries the launch specs the house projects need.
---

# LAN and supervised servers

## The rule

- A server the user's devices depend on (a phone-facing LAN server, a
  webhook receiver, a long-running service) started through the hub MUST
  use `detached: true` — it survives broker/daemon restarts AND all omp
  exits (it implies persist). `persist: true` alone is NOT enough: it
  survives the last-omp teardown but the daemon's own restarts still
  SIGTERM the process tree (2026-08-16: the loft-serve died this way
  twice — clean SIGTERM in the logs, no crash, `restart: no` left it
  down).
- `ready` conditions gate the start (a port and/or a log banner) — the
  start is not "done" until the server actually serves.
- The Makefile cannot set these: they are launcher options, not command
  options. `make serve` in a plain terminal is the normal foreground dev
  server (Ctrl-C stops it; nothing to configure).

## The launch specs

### the-loft / family-history-album — the review surface's LAN server

The phone's view of the family-history app. Hub launch:

- application: `make`, args: `["serve"]`, cwd: the repo root
- `detached: true` (survives broker restarts + all omp exits — REQUIRED,
  see the rule)
- ready: `{ port: 8000, log: "Application startup complete" }`

`make serve` runs `loft serve --host 0.0.0.0 --port 8000 --reload`:
the backend auto-reloads on source changes (watchfiles; watch roots are
`tools/` + `tests/` only), and frontend changes need a browser refresh
only (the app is served without a build step). The hub process is named
`loft-serve`.
