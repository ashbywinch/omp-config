---
name: litellm-gateway
description: LiteLLM proxy for Paseo/OMP — provider failover chain (GLM -> Muse -> OpenCode -> DeepSeek), blue-green swaps, rollback-first operations
---

# LiteLLM Gateway

One local endpoint (`http://localhost:4000/v1`) that owns the model fallback
chain. Clients (omp, Paseo agents) ask for model `primary`; LiteLLM routes
through the chain and fails over per request. Replaces Cloudflare AI Gateway
for the text default; Cloudflare stays configured as the manual rollback.

## The chain (what `primary` means)

`primary` = GLM-5.3-Flash (z.ai Coding Plan) → Muse Spark (OpenCode) →
DeepSeek V4 Flash (OpenCode) → DeepSeek (direct). Chain order and models live
in the LiteLLM config only — clients never change. Editing the chain never
touches omp/Paseo config.

## Blue-green layout

```
~/.paseo/litellm/
  config.green.yaml    # last-known-good chain (never edit in place)
  config.blue.yaml     # staging chain (edit THIS for a change)
  config.current.yaml  # symlink -> green|blue ; what :4000 serves
  test.sh              # validate a config on :4001 (3 probes, no live traffic)
  swap.sh              # status / activate / rollback
  env                  # keys: ZAI_API_KEY, OPENCODE_API_KEY, DEEPSEEK_API_KEY
```

Service: `litellm.service` (systemd --user), `ExecStart` uses
`config.current.yaml`, `EnvironmentFile=~/.paseo/litellm/env`.

## ROLLBACK FIRST — non-negotiable

BEFORE running any `swap.sh activate` (or any change to the live chain):

1. Print the rollback command and make the user acknowledge it.
2. The rollback must never depend on a model provider: it is a symlink flip
   plus a systemd restart, runnable from any terminal even if every LLM call
   is failing.

```
# Revert LiteLLM chain to last-known-good:
~/.paseo/litellm/swap.sh rollback
# manual equivalent:
ln -sf ~/.paseo/litellm/config.green.yaml ~/.paseo/litellm/config.current.yaml
systemctl --user restart litellm

# Revert omp/Paseo to Cloudflare (skip LiteLLM entirely):
# edit ~/.omp/agent/config.yml -> modelRoles.default (and advisor):
#   cloudflare-gateway/dynamic/fallback2
# (the cloudflare-gateway provider entry in ~/.omp/agent/models.yml remains)
```

## Operations

```bash
~/.paseo/litellm/swap.sh status    # which side is live
~/.paseo/litellm/test.sh           # validate BLUE on :4001 (serve/SSE/cascade)
~/.paseo/litellm/swap.sh activate  # current -> blue + restart (prints rollback first)
~/.paseo/litellm/swap.sh rollback  # current -> green + restart
systemctl --user status litellm    # service health
curl -s http://localhost:4000/health/readiness
```

`test.sh` probes: `primary` returns 200 (GLM healthy), streamed `primary` ends
with `[DONE]`, and a copy of the config with GLM's endpoint killed still
returns 200 from a fallback model. NEVER activate a config that fails `test.sh`.

## Changing the chain

1. Edit `config.blue.yaml` (order, models, keys, timeouts).
2. `~/.paseo/litellm/test.sh` — must pass ALL probes.
3. Print the rollback command (above) and confirm the user has it.
4. `~/.paseo/litellm/swap.sh activate`.
5. Verify `/health/readiness` and a `primary` call.
6. After a stable soak, promote blue → green is NOT automatic: copy
   `config.blue.yaml` over `config.green.yaml` ONLY when you are ready for
   the new chain to be the rollback target.

## Clients

- omp/Paseo agents: `litellm/primary` in `modelRoles`; `litellm` provider
  (`baseUrl http://localhost:4000/v1`) in `~/.omp/agent/models.yml`.
  Restart the omp session to pick up provider/model changes.
- `designer`/`vision` roles: still `cloudflare-gateway/dynamic/image`
  (Cloudflare image route, free of the text-chain).
- PR-Agent (GitHub Actions): stays on Cloudflare — it cannot reach
  localhost, and direct provider calls there never used the shim.

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
     ~/.paseo/agents --include='*.json' | xargs sed -i \
     's/"model": "cloudflare-gateway\/dynamic\/fallback2"/"model": "litellm\/primary"/g'
   ```

3. `systemctl --user start paseo`, then re-grep: expect 0 hits.

New sessions follow `agents.providers.omp.models[].isDefault` in
`~/.paseo/config.json`; the per-session pin is what the Paseo UI model
dropdown sets.

## Diagnostics

- Provider-side errors — z.ai `429` (wrong endpoint for the Coding Plan
  key), `DataPolicyError` (OpenCode workspace opt-in), `MonthlyLimitError`
  (OpenCode spend cap) — meanings and fixes are canonical in
  `skill://cloudflare-ai-gateway/references/adding-providers.md`.
- Keys live in `~/.paseo/litellm/env` (600); never print them.