---
name: paseo-daemon-troubleshooting
description: Diagnose a down or unhealthy Paseo daemon — OOM kills, relay/E2EE failures, event-loop starvation, memory pressure, client reconnect churn, MCP accumulation
---

# Paseo Daemon Troubleshooting

## Architecture facts

- **Service**: user systemd unit `paseo.service` (`~/.config/systemd/user/paseo.service`),
  runs `~/.paseo/start.sh` → `paseo daemon run --home ~/.paseo`. `Restart=on-failure`, `RestartSec=5`.
  `daemon start --foreground` does not exist; a start.sh that passes it crash-loops the
  unit — exit 1, `NRestarts` climbing every 5s, the daemon never listening.
- **One cgroup for everything**: supervisor (node) → "Paseo Daemon" → spawned agent sessions
  (omp rpc-ui, opencode serve, headless chrome, brokers, python runners). `KillMode=control-group`:
  any restart or OOM kill takes ALL of them down; the app re-spawns sessions afterward.
- **Listen**: `0.0.0.0:6767` (config.json `daemon.listen`); the local CLI talks to `127.0.0.1:6767`.
- **Relay**: `wss://relay.paseo.sh` (E2EE). Identity = `~/.paseo/daemon-keypair.json` + `server-id`.
- **Logs**: `~/.paseo/daemon.log` — JSON lines, 30s window-stats spam, 10MB rotation.
- **Guardrails in place**: unit `MemoryMax=6G`, `OOMPolicy=continue`; 16G swap
  (`/swapfile` 2G + `/swapfile2` 14G).

## Known failure modes

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
  "Connection closed during handshake: 1006", `relay_control_disconnected` every ~10s,
  surviving daemon restarts → **relay/cloud-side**. The machine is exculpated when
  keypair/server-id mtimes predate the break, the daemon version is current on npm, and
  `curl https://relay.paseo.sh/` connects fast.
  Workaround: direct LAN endpoint — app manual server `192.168.1.251:6767`; the relay
  stays enabled and reconnects automatically when the cloud recovers.
- **Agent provider wrapper writes to stdout.** `config.json` `agents.providers.omp.command`
  is `~/.paseo/omp-yolo.sh`, whose `curl _tag` call leaked the proxy's `ok` body into omp's
  JSONL RPC stream. Daemon log then shows `Ignoring invalid OMP RPC frame` with
  `"line":"ok{\"type\":\"ready\",...}"` and `Timed out waiting for OMP to become ready` on
  `fetch_agent_timeline_request` / `send_agent_message_request`. Any wrapper around a provider
  CLI MUST keep stdout clean for the protocol (redirect every helper command to `/dev/null`).

## Client churn, MCP accumulation and config edits

Read the 30s window stats before anything else:

    grep ws_runtime_metrics ~/.paseo/daemon.log | tail -1

`memory.heapUsed`, `eventLoopDelay.maxMs`, `bufferedAmount.max`, `latency[]` and
`counters` localise a fault in one line. A slow handler with a small
`bufferedAmount` means the client or the network, not the daemon.

- **Connection churn looks like slowness.** The app owns liveness: 10s heartbeat,
  15s timeout, two failures then dispose (`1001 Liveness check timed out`), plus a
  3s verification ping (`Connection verification failed`). The daemon cannot relax
  either. Symptoms: reconnect every 20–45s, thousands of `ws_send_failed` /
  `Failed to emit source frame`, `Liveness check timed out` as the disconnect
  reason, app diagnostic showing high Active RTT against a low TCP probe.
- **Check the relay even when the app reports `relay: inactive`.** Flapping
  `relay_data_connected/disconnected` tears down the session socket; when the app
  has a direct LAN path, set `daemon.relay.enabled: false` and
  `paseo daemon reload` — keep the relay only for off-LAN access.
- **`checkout_status`/`checkout_pr_status` taking seconds is network-bound** and
  independent of message loading. Do not conflate the two.
- **MCP children accumulate.** OpenCode keeps one MCP process per (server,
  directory) for the life of the shared server and never evicts it;
  `idleRuntimeCleanup` reaps agent runtimes, not these.
- **Watcher fleets hit inotify limits.** A per-repo watcher uses one inotify
  instance per watched directory, not one per repo; roughly 20 repos exceeds the
  default `fs.inotify.max_user_instances` (128). Raise the limit or watch only
  active repos.
- **Validate config before reloading.** An unknown key fails the whole reload.
  Useful keys: `daemon.relay.enabled`, `agents.idleRuntimeCleanup`,
  `agents.metadataGeneration.providers` (empty means automatic cheap-model
  fallback). `paseo daemon reload` applies them without a restart; plugins are
  managed with `paseo plugin`.

## Troubleshooting playbook (in order)

0. Window stats first (command above) — heap, event-loop max, buffered amount,
   per-request latency, agent/timeline counts.
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
  offers are relay-only in v0.2.5; no LAN discovery (mDNS) exists. The supported form
  is `daemon.relay.enabled: false` plus `paseo daemon reload`; re-enable it before
  relying on off-LAN access.
- Never kill an MCP child process to reclaim memory — the session loses its tools
  permanently, and only a config change or a daemon restart brings them back. Stop the
  shared OpenCode server (safe) or restart the daemon instead.
- Bind a specific LAN IP in `daemon.listen` — breaks the local CLI (needs 127.0.0.1).
  Use `0.0.0.0:6767`.
