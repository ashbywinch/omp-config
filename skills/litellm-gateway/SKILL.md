---
name: litellm-gateway
description: LiteLLM proxy for Paseo/OMP — the local failover chain, the blue-green swap procedure, and rollback-first operations
---

# LiteLLM Gateway

One local endpoint (`http://localhost:4000/v1`) owns the model failover chain:
clients (omp, Paseo agents) ask for model `primary`, LiteLLM routes through the
chain and fails over per request. The text default runs through this proxy;
Cloudflare AI Gateway stays configured as the manual rollback.

## Where the originals live

The chain, the commands and the gate are defined in these files. Read them
there — never restate their contents in a doc or a skill.

```
~/.paseo/litellm/
  config.blue.yaml        the chain to edit: `model_list` order (head first) and
                          `fallbacks:` (the order after it), plus the header
                          comments carrying the provider constraints
  config.green.yaml       the rollback target: the chain the last promote left
                          in place
  config.green.yaml.prev  the chain the last promote replaced (one step back)
  config.current.yaml     symlink -> config.green.yaml or config.blue.yaml ;
                          what :4000 serves
  swap.sh                 the state machine — run it with no arguments for the
                          subcommand list; `swap.sh status` prints the live side,
                          whether the sides differ, health, the last gate outcome
                          (.gate-state), and the next command
  test.sh                 the gate — its header documents the probes, the
                          chain-shape contract it parses, and the per-member
                          error/consequence output on FAIL
  env                     the API keys (600; never print them)
  .gate-state             the last gate outcome keyed to blue's content hash —
                          status withholds activate/promote while it is FAIL
```

Service: `litellm.service` (systemd --user), serving `config.current.yaml` with
`EnvironmentFile` = `env`.

## Sides and the live side

`BLUE` is `config.blue.yaml`, the side to edit. `GREEN` is `config.green.yaml`,
the rollback target. `config.current.yaml` symlinks the file `:4000` serves.
`swap.sh status` reports whether the sides are identical — both files hold the
same bytes.

Never edit the live side. Steady state is `live = GREEN` with identical sides,
which leaves BLUE free to stage the next change. Nothing on the filesystem
enforces this — the check is the guard.

## The gate

`test.sh` proves every chain member serves on its own, so a failing member
cannot hide behind a working fallback, and it asserts real content — a chain
that answers with empty messages is not working.

## Chain members that fail report their provider error

A chain member is one model in `model_list` that the alias can fall through to:
the head first, then `fallbacks` in order. `test.sh` probes each member alone
with fallbacks disabled and prints the failing member's provider error (status,
type, message, remediation URL) plus which members ride instead.

Report that error as printed. A member failing on exhausted credit, a billing
gate, or "model disabled" is not classified here: whether it needs a fix or is
an acceptable fallback is the operator's decision. Pass the printed errors to
the user verbatim and wait for their call before any live-side command.

`--yes` is the tool-level acknowledgment — it never bypasses the probe. The
routes to a passing gate are a provider-side fix or reshaping the chain
(drop/swap the failing member).

## Rollback first

Run `swap.sh status`: it prints the live side, whether the sides differ, health,
the last gate outcome, and the next command. Run the command its `next:` line
names.

- `swap.sh rollback` re-links GREEN and restarts. It reverts a soak
  (`live = BLUE`); in every other state it restarts onto the chain already
  live, so it changes nothing.
- `promote --yes` makes GREEN the live chain and saves the outgoing chain to
  `config.green.yaml.prev`. `swap.sh promote` prints the one-step undo, so run
  it without `--yes` and state that output before promoting.
- With `live = BLUE`, run `skill://litellm-gateway/examples/snapshot-live.sh`
  before anything else: it prints the timestamped backup and the exact restore
  lines. State that output plus the Cloudflare fallback
  (`~/.omp/agent/config.yml` → `modelRoles.default:
  cloudflare-gateway/dynamic/fallback2`) before `test`, `activate --yes`, or
  `promote --yes`. State every path as the full filesystem path the tool
  printed — never `swap.sh`, `skill://...`, or `~` shorthand. Never state a
  recovery that leaves the live head unrestored.
- Never run `promote --yes` before stating that recovery and receiving the
  user's acknowledgment.
- At steady state the dry run (`swap.sh activate` without `--yes`) prints the
  rollback lines (full paths): copy them exactly, never retype or shorten, then
  wait for acknowledgment before `test` or `activate --yes`.
- Never stage and activate in one turn: edit, gate, report, wait.

## Traps

- Prove the chain with `swap.sh test`, which probes every member alone. A 200
  from the alias proves that one member answered, nothing more.
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
overrides the default in `~/.paseo/config.json`.

Change a model in the LiteLLM chain (`config.blue.yaml`). Override it in
`~/.paseo/config.json` only when the user explicitly asks for that session to
bypass the chain.

Migrate existing pins with
`skill://litellm-gateway/examples/migrate-paseo-pins.sh`, daemon stopped:
in-memory session state flushes back on shutdown and reverts an edit made
against a live daemon.

## Diagnostics

- Provider-side errors (`DataPolicyError`, `MonthlyLimitError`, region and
  billing gates) are fixed on the provider side, not in this chain's config;
  while they persist they block every live-side command (`Chain members that
  fail report their provider error`). Provider configuration for these routes
  is in `skill://cloudflare-ai-gateway`.
- Keys live in `~/.paseo/litellm/env`; never print them.
