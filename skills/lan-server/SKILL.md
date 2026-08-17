---
name: lan-server
description: |
  Launching a project's long-running server through the hub (supervised).
  User-facing servers MUST be started with detached: true and a ready
  condition — persist: true alone is not enough: it survives the last-omp
  teardown but not daemon restarts, and the server dies silently mid-use.
  Links project launch specs; does not restate them.
---

# LAN and supervised servers

## The rule

- A server the user's devices depend on (a phone-facing LAN server, a
  webhook receiver, a long-running service) started through the hub MUST
  use `detached: true` — it survives broker/daemon restarts AND all omp
  exits (it implies persist). `persist: true` alone is NOT enough: it
  survives the last-omp teardown but the daemon's own restarts still
  SIGTERM the process tree; with `restart: no` the server stays down.
- `ready` conditions gate the start (a port and/or a log banner) — the
  start is not "done" until the server actually serves.
- The Makefile cannot set these: they are launcher options, not command
  options. `make serve` in a plain terminal is the normal foreground dev
  server (Ctrl-C stops it; nothing to configure).

## Project launch specs

Each house project's hub launch spec (application, args, detached flag,
ready conditions) lives in that project's own docs — link it here, never
restate it. The projects currently using supervised launches: the-loft /
family-history-album (see its TECH-SPEC / README).