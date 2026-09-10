---
name: litellm-gateway
description: LiteLLM proxy for Paseo/OMP — deterministic blue-green chain runbook (edit blue -> test -> activate -> promote), rollback-first, one local failover chain
---

# LiteLLM Gateway

One local endpoint (`http://localhost:4000/v1`) owns the model fallback chain.
Clients (omp, Paseo agents) ask for model `primary`; LiteLLM routes through the
chain and fails over per request. Replaces Cloudflare AI Gateway for the text
default; Cloudflare stays configured as the manual rollback.

## The chain (what `primary` means)

`primary` = DeepSeek V4 Flash (OpenCode Go) → Muse Spark (OpenCode) →
DeepSeek V4 Flash (direct DeepSeek API). Chain order and models live in the
LiteLLM config only — clients never change. Editing the chain never touches
omp/Paseo config. (z.ai / GLM was removed from the chain 2026-09-10.)

## Blue-green: the sides and the invariant

```
~/.paseo/litellm/
  config.green.yaml       last-known-good chain — the rollback target
  config.blue.yaml        the ONLY side you edit
  config.green.yaml.prev  chain replaced at the last promote (one step back)
  config.current.yaml     symlink -> green|blue ; what :4000 serves
  swap.sh                 status | test | activate --yes | promote --yes | rollback
  test.sh                 validates a config on :4001 (3 probes, no live traffic)
  env                     keys: OPENCODE_API_KEY, DEEPSEEK_API_KEY (600; never print)
                          (+ ZAI_API_KEY while config.green.yaml.prev still needs it)
```

INVARIANT: the live side is never the side you edit. Steady state is
`live = GREEN` with `blue == green`; blue is then free staging.

Service: `litellm.service` (systemd --user); `ExecStart` serves
`config.current.yaml`, `EnvironmentFile=~/.paseo/litellm/env`.

## Read the state, then follow the matching row

`~/.paseo/litellm/swap.sh status` prints the live side, whether the sides
differ, health, and the next command. This table is the whole decision
procedure — no judgement calls:

| live side | sides | meaning | next |
|---|---|---|---|
| GREEN | identical | steady state | edit `config.blue.yaml` |
| GREEN | differ | a change is staged, not live | `swap.sh test` → `swap.sh activate --yes` |
| BLUE | differ | new chain live, green = rollback target | soak → `swap.sh promote --yes` (or `swap.sh rollback` to revert) |
| BLUE | identical | green == blue, so live can return to green for free | `swap.sh promote --yes` |
| any | any | `health: NOT HEALTHY` | `swap.sh rollback` |

## The change cycle — exact commands

```bash
cd ~/.paseo/litellm
swap.sh status                 # confirm: live side GREEN, blue free to edit
${EDITOR:-vi} config.blue.yaml  # order, models, keys, timeouts — blue ONLY
swap.sh test                   # gate: 3 probes must PASS (≈20 s, :4001 only)
swap.sh activate               # dry run: prints rollback + plan, switches nothing
swap.sh activate --yes         # re-runs the gate, then live -> blue, then verifies
# ... soak: use the system normally ...
swap.sh promote --yes          # gate, green.prev <- green, green <- blue, live -> green
```

Expected ends: activate prints `served by: <model>` naming the upstream that
answered; promote prints `promoted: live side GREEN == BLUE`.

`activate` and `promote` without `--yes` are dry runs: they print the plan and
the rollback/undo command, then exit 1. The acknowledgment step is mechanical,
not a matter of remembering.

## What each part guarantees

- `test.sh` — 3 probes on a throwaway instance at :4001, no live traffic:
  `primary` → 200, streamed `primary` ends with `[DONE]`, and a copy of the
  config with the head deployment's `api_base` patched to an unreachable host
  still returns 200 from a fallback. The cascade probe takes the first
  `api_base` line in the file (that is the head deployment's) and patches it to
  `http://127.0.0.1:9/`, so it stays a real test when the head changes — it
  cannot pass vacuously.
- `swap.sh activate` — refuses when BLUE is already live (the one edit
  blue-green exists to prevent) and refuses unless the gate passes. The flip
  is: symlink, restart, poll `/health/readiness` (≤120 s), then a real
  `primary` call. Any failure prints the rollback command.
- `swap.sh promote` — refuses unless BLUE is live; runs the same gate; saves
  the outgoing chain to `config.green.yaml.prev`; copies blue → green and
  asserts `cmp` equality; then returns live to GREEN (byte-identical content,
  so zero behaviour change). This is what makes `rollback` content-neutral in
  steady state and frees blue for the next change.
- `swap.sh rollback` — the emergency path, depending on NOTHING but the two
  config files and systemd: no provider, no env file, no gate. It flips to
  GREEN, restarts, and waits for health. Run it even if every LLM call is
  failing. `rollback` and the second half of `promote` are the same code path,
  so the emergency path is exercised on every promote.

## ROLLBACK FIRST — non-negotiable

Before any command that changes the live side, print the rollback command and
make the user acknowledge it. `swap.sh` prints it itself: on the dry run, on
activate, and on every failure.

```
~/.paseo/litellm/swap.sh rollback                # first choice, from any terminal
# manual equivalent, if the script itself is broken:
ln -sf ~/.paseo/litellm/config.green.yaml ~/.paseo/litellm/config.current.yaml
systemctl --user restart litellm
# undoing a PROMOTION (usable once): the chain the promote replaced
# WARNING: works only once — a second promotion overwrites .prev
cp ~/.paseo/litellm/config.green.yaml.prev ~/.paseo/litellm/config.green.yaml
~/.paseo/litellm/swap.sh rollback
# the prev chain needs its own key in env — keep ZAI_API_KEY until prev is dropped
# all the way back to Cloudflare (no LiteLLM):
#   ~/.omp/agent/config.yml -> modelRoles.default: cloudflare-gateway/dynamic/fallback2
```

## Traps (each cost a real incident)

- NEVER edit the live side — a restart mid-edit serves the half-staged config.
  The guard is the check, not a lock: `config.current.yaml` is a symlink and
  the filesystem does not stop you writing to the live side's config file.
  Always run `swap.sh status` first and edit only the side it does not name as
  live. `activate` refuses to make the side you are editing the live one.
- NEVER promote to make a failure go away: promotion runs the same gate, but it
  is still the step that copies the live chain over the rollback target. If what
  you are working around is something the gate cannot see, green is overwritten
  with the bad chain — `rollback` no longer reverts it, and the ways back are the
  one-step `.prev` restore (until the next promote) or the manual Cloudflare
  switch in `~/.omp/agent/config.yml`.
- A restart takes tens of seconds; `swap.sh` polls health for up to 120 s. A
  shell that times out while waiting is not evidence of failure — check
  `swap.sh status`.
- `test.sh` needs the keys in the environment: run it as `swap.sh test` (which
  sources `env`), never by hand from a bare shell.

## Clients

- omp/Paseo agents: `litellm/primary` in `modelRoles`; `litellm` provider
  (`baseUrl http://localhost:4000/v1`) in `~/.omp/agent/models.yml`.
  Restart the omp session to pick up provider/model changes.
- `designer`/`vision` roles: still `cloudflare-gateway/dynamic/image`
  (Cloudflare image route, free of the text-chain).
- PR-Agent (GitHub Actions): stays on Cloudflare — it cannot reach
  localhost.

### Paseo sessions pin the model per session — restarts never migrate them

Each session stores its model in `~/.paseo/agents/<worktree>/<agent>.json`
(`config.model`, duplicated in `runtimeInfo.model` and
`persistence.metadata.model`). Those pins OVERRIDE `modelRoles.default`:
sessions created before the migration keep
`cloudflare-gateway/dynamic/fallback2` no matter how often the daemon
restarts. Migration = rewrite the pins:

1. `systemctl --user stop paseo` FIRST — editing under a live daemon loses
   the race: dirty in-memory session state flushes back on shutdown and
   reverts the edit (observed: 4 of 21 pins reverted through a live edit).
2. Rewrite pins with an exact match (spares the historical `lastError`
   strings, which reference the old model with `model=` syntax):

   ```bash
   grep -rl '"model": "cloudflare-gateway/dynamic/fallback2"' \
     ~/.paseo/agents --include='*.json' | xargs -r sed -i \
     's/"model": "cloudflare-gateway\/dynamic\/fallback2"/"model": "litellm\/primary"/g'
   ```

3. `systemctl --user start paseo`, then re-grep: expect 0 hits.

New sessions follow `agents.providers.omp.models[].isDefault` in
`~/.paseo/config.json`; the per-session pin is what the Paseo UI model
dropdown sets.

## Diagnostics

- OpenCode errors: `DataPolicyError` = the workspace has not opted in to its
  data policy; `MonthlyLimitError` = the OpenCode spend cap is reached. Both
  are fixed on the OpenCode side, not in this chain's config.
- Provider configuration for these routes (Cloudflare, OpenCode, DeepSeek) is
  in `skill://cloudflare-ai-gateway`.
- Keys live in `~/.paseo/litellm/env` (600); never print them.
