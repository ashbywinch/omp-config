---
name: paseo-daemon-troubleshooting
description: Diagnose a down or unhealthy Paseo daemon — OOM kills, relay/E2EE failures, event-loop starvation, memory pressure
---

# Paseo Daemon Troubleshooting

## Architecture facts (as of 2026-08-03)

- **Service**: user systemd unit `paseo.service` (`~/.config/systemd/user/paseo.service`),
  runs `~/.paseo/start.sh` → `paseo daemon start --foreground`. `Restart=on-failure`, `RestartSec=5`.
- **One cgroup for everything**: supervisor (node) → "Paseo Daemon" → spawned agent sessions
  (omp rpc-ui, opencode serve, headless chrome, brokers, python runners). `KillMode=control-group`:
  any restart or OOM kill takes ALL of them down; the app re-spawns sessions afterward.
- **Listen**: `0.0.0.0:6767` (config.json `daemon.listen`); the local CLI talks to `127.0.0.1:6767`.
- **Relay**: `wss://relay.paseo.sh` (E2EE). Identity = `~/.paseo/daemon-keypair.json` + `server-id`.
- **Logs**: `~/.paseo/daemon.log` — JSON lines, 30s window-stats spam, 10MB rotation.
- **Guardrails in place**: unit `MemoryMax=6G`, `OOMPolicy=continue`; 16G swap
  (`/swapfile` 2G + `/swapfile2` 14G).

## Known failure modes & what was done (2026-08-03)

- **OOM kill of the whole service**: kernel `global_oom` picked a chrome process inside the
  cgroup (oom_score_adj=300) → `paseo.service: Failed with result 'oom-kill'`, down 2.5h.
  Cause: 7.1G box; cgroup ~4.6G+ (3 omps + 5 opencodes + browsers) exhausted RAM + 2G swap.
  Fixes: 14G `/swapfile2` (OOM now effectively impossible), `MemoryMax=6G` +
  `OOMPolicy=continue` (worst case kills one session, never the tree).
- **"Down" ≠ dead**: daemon process alive but relay dead and/or event loop starved.
  Symptoms: `paseo daemon status` takes 5–10s with note "daemon detail request to
  127.0.0.1:6767 failed"; log shows `ws_slow_request`. Cause: daemon pages swapped out,
  every access page-faults to disk. Fix: reduce load / restart.
- **Relay E2EE handshake failures**: `relay_e2ee_handshake_failed`,
  "Connection closed during handshake: 1006", `relay_control_disconnected` every ~10s.
  Started ~19:45 UTC 2026-08-03, survives daemon restarts → **relay/cloud-side**.
  Machine is exculpated when: keypair/server-id mtimes predate the break, daemon version
  == latest on npm, and `curl https://relay.paseo.sh/` connects fast (it does).
  Workaround: direct LAN endpoint — app manual server `192.168.1.251:6767`; the relay
  stays enabled and reconnects automatically when the cloud recovers.

## Troubleshooting playbook (in order)

1. `systemctl --user status paseo` — active? Last `Failed with result`: oom-kill / resources / exit-code.
2. `journalctl --user -u paseo -n 50` — restart history; `journalctl -k | grep -i oom` for kernel kills.
3. `paseo daemon status` — "detail request failed" note = slow event loop, not a dead daemon.
4. `free -h` + `uptime` — swap 100% used / high load → memory pressure: add a swapfile,
   close sessions, or inspect MemoryMax behavior.
5. Memory census: cgroup RSS+swap per bucket (omp / opencode / chrome / brokers). Chrome is
   usually the smallest bucket; the omp+opencode fleet is the base load (~4G with 3+5).
6. Relay diagnosis: `grep -E 'relay_e2ee_handshake_failed|ws_slow_request|relay_control_disconnected' daemon.log`;
   `curl -sI https://relay.paseo.sh/` (fast = network fine); stat keypair/server-id mtimes.
7. Restart to recover: `systemctl --user restart paseo` — kills ALL sessions in the cgroup
   (app re-spawns them); use `--no-block` if the caller might be inside the cgroup.
8. Verify after restart: `ss -tlnp | grep 6767`, `grep 'Server listening' daemon.log`,
   first `relay_data_connected` in the log.

## Never do

- `truncate`/overwrite the live `/swapfile` (corrupts live swap → crash). Add a NEW file:
  `fallocate -l <size> /swapfile2 && chmod 600 && mkswap && swapon` + fstab line.
- Delete/regenerate `daemon-keypair.json` or `server-id` (breaks app pairing).
- Disable the relay (`--no-relay`) unless a direct client path is confirmed — pairing
  offers are relay-only in v0.2.5; no LAN discovery (mDNS) exists.
- Bind a specific LAN IP in `daemon.listen` — breaks the local CLI (needs 127.0.0.1).
  Use `0.0.0.0:6767`.
