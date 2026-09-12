---
name: litellm-gateway
description: LiteLLM proxy for Paseo/OMP — the local failover chain, the blue-green swap procedure, and rollback-first operations
---

# LiteLLM Gateway

One local endpoint (`http://localhost:4000/v1`) owns the model failover chain:
clients (omp, Paseo agents) ask for model `primary`, LiteLLM routes through the
chain and fails over per request. Replaces Cloudflare AI Gateway for the text
default; Cloudflare stays configured as the manual rollback.

## Where the originals live

The chain, the commands and the gate are defined in these files. Read them
there — never restate their contents in a doc or a skill.

```
~/.paseo/litellm/
  config.blue.yaml        the chain to edit: `model_list` order (head first) and
                          `fallbacks:` (the order after it), plus the header
                          comments carrying the provider constraints
  config.green.yaml       the live chain / rollback target
  config.green.yaml.prev  the chain the last promote replaced (one step back)
  config.current.yaml     symlink -> green|blue ; what :4000 serves
  swap.sh                 the state machine — run it with no arguments for the
                          subcommand list; `swap.sh status` prints the live side,
                          whether the sides differ, health, and the next command
  test.sh                 the gate — its header documents the probes and the
                          chain-shape contract it parses
  env                     the API keys (600; never print them)
```

Service: `litellm.service` (systemd --user), serving `config.current.yaml` with
`EnvironmentFile` = `env`.

## The invariant

The live side is never the side you edit. `swap.sh status` names the live side;
steady state is `live = GREEN` with `blue == green`, which leaves blue free to
stage the next change. Nothing on the filesystem enforces this — the check is
the guard.

## The gate

Never activate a config that fails `test.sh`; the live-side commands run it
themselves and refuse on failure. The gate proves every chain member serves on
its own, so a broken member cannot hide behind a working fallback, and it
asserts real content — a chain that answers with empty messages is not working.

## Rollback first — the rollback is on screen before any live-side command runs

- The only `swap.sh` invocations allowed before the rollback statement are
  `swap.sh status` and the dry run (`swap.sh activate` without `--yes`):
  both change nothing, and the dry run prints the rollback lines. Copy those
  lines into your reply — never retype from memory.
- Never run `swap.sh test` or `swap.sh activate --yes` before stating that
  rollback and receiving the user's acknowledgment.
- Never stage and activate in one turn: edit, gate, report, wait.

`swap.sh rollback` is the emergency path: it depends on nothing but the two
config files and systemd — no provider, no env file, no gate — so it runs from
any terminal while every LLM call is failing. The Cloudflare fallback for
omp/Paseo is in `swap.sh`'s rollback output.

## Traps

- Never treat "the alias answers" as proof the chain works — only the gate's
  member probe is that proof.
- Never edit the live side: a restart mid-edit serves the half-staged config.
- Never promote to escape a failure: promotion copies the live chain over the
  rollback target, so the bad chain becomes the rollback target too. `.prev`
  undoes one promotion, once.
- A restart takes tens of seconds; a shell that times out while waiting is not
  evidence of failure — check `swap.sh status`.

## Clients

- omp/Paseo agents: the `litellm` provider entry and the role pointing at it
  live in `~/.omp/agent/models.yml` and `~/.omp/agent/config.yml`.
- `designer`/`vision` roles and PR-Agent stay on Cloudflare — PR-Agent cannot
  reach localhost.

### Paseo sessions pin their model — restarts never migrate them

A session's model lives in `~/.paseo/agents/<worktree>/<agent>.json` and
overrides the default in `~/.paseo/config.json`. Migrate the pins with
`skill://litellm-gateway/examples/migrate-paseo-pins.sh`, with the daemon
stopped: in-memory session state flushes back on shutdown and reverts an edit
made against a live daemon.

## Diagnostics

- Provider-side errors (`DataPolicyError`, `MonthlyLimitError`) are fixed on the
  provider side, not in this chain's config; provider configuration for these
  routes is in `skill://cloudflare-ai-gateway`.
- Keys live in `~/.paseo/litellm/env`; never print them.
