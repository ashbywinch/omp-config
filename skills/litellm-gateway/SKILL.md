---
name: litellm-gateway
description: LiteLLM proxy for local model failover — the chain, the blue-green swap procedure, and rollback-first operations
---

# LiteLLM gateway

One local endpoint (`http://localhost:4000/v1`) belongs to LiteLLM, the local
proxy for model failover. A client asks for model `primary` — the alias the
chain answers to; the proxy routes through the chain and fails over per
request. Which gateway each client uses is in `skill://cloudflare-ai-gateway`.

LiteLLM calls each model at the URL its config gives, so a provider serving at
its own path is reachable here — z.ai's Coding Plan is the worked example. It
serves only workloads on this machine.

## Where the originals live

The chain and the gate are defined in these files. Read them there — never
restate their contents in a doc or a skill.

The tooling is sourced from `ashbywinch/bluegreen-config` and installed into the
state directory by `make install` (copies, not symlinks); `make check-installed`
fails when the installed copy drifts from the repo. Change a script in the repo,
install, then operate.

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
  snapshot-live.sh        the pre-switch snapshot — prints a timestamped backup
                          of the live side and the exact restore lines
  .gate-state             the last gate outcome keyed to blue's content hash —
                          status withholds activate/promote while it is FAIL
```

Service: `litellm.service` (systemd --user); `ExecStart` sources `~/.secrets` —
the one file holding the keys, so there is no `EnvironmentFile` — and serves
`config.current.yaml`.

## Sides and the live side

`BLUE` (`config.blue.yaml`) is the side to edit. `GREEN` (`config.green.yaml`) is
the chain that keeps serving. `config.current.yaml` symlinks whichever one `:4000`
reads, so "live" means the side that symlink points at.

At rest both sides hold the same chain: nothing is staged, and the next change is
an edit to BLUE. An edit makes the sides differ, and that difference *is* the
staged change — invisible to `:4000` until a live-side command points
`config.current.yaml` at BLUE. When the sides hold the same chain again the staged
change is gone: it either went live or was reverted.

Never edit the live side. Nothing on the filesystem enforces this — the check is
the guard.

## The gate

`test.sh` proves every chain member serves on its own, so a failing member
cannot hide behind a working fallback, and it asserts real content — a chain
that answers with empty messages is not working.

## The chain exists to spend two allowances in turn

The chain's shape is a requirement, not a preference: every subscription the
user pays for sits in `model_list`, always. Which member has spent its
allowance is `test.sh`'s output, not a value kept anywhere.

A subscription that has spent its monthly allowance answers 429 with a
Retry-After measured in days. `test.sh` reports that member **EXHAUSTED** and
does not fail the gate on it — it is the designed state for half of every
month, and the chain rides the next member automatically, in either direction,
for as long as it lasts. There is no reordering step and no order to maintain:
a fixed order self-corrects through cooldown.

**Never delete or drop an exhausted member to get a green gate.** Removing it
leaves one subscription wearing a chain's shape, and the traffic the other
carried moves to per-token billing — which looks like a working chain until the
bill. An exhausted subscription is the half of the allowance that carries the
traffic when the other one runs out.

## Chain members that fail report their provider error

A chain member is one model in `model_list` that the alias can fall through to:
the head first, then `fallbacks` in order. `test.sh` probes each member alone
with fallbacks disabled and prints the failing member's HTTP status, error type
and message, plus which members ride instead.

Report that error as printed. A member failing on a provider-side error — a
4xx/5xx, an auth or billing rejection, a data-policy or region gate, "model
disabled", empty content — **is not classified here: whether it needs a fix, a
different member, or a paid route is the operator's decision.** Pass the printed
errors to the user verbatim and wait for their call before any live-side
command. Never reach for a fix just to get the gate green: swapping in a member
that bills per token, or any change that moves traffic onto a paid endpoint, can
cost the user real money without their knowledge. A chain that quietly papered
over a failure looks exactly like one that works — until the bill.

The one pre-classified case is `EXHAUSTED`: spent allowance changes nothing
about the chain and is never the operator's problem to solve. Everything else
the gate calls `FAIL` is theirs to decide.

`--yes` is the tool-level acknowledgment — it never bypasses the probe. The
routes to a passing gate are a provider-side fix, or a reshape the operator has
approved. Reshaping is never something to do unasked: never delete an exhausted
member, and never swap in a paid route to turn red green.

## Rollback first

Run `swap.sh status`: it prints the live side, whether the sides differ, health,
the last gate outcome, and the next command. Run the command its `next:` line
names.

- `swap.sh rollback` re-links GREEN and restarts. It reverts a soak
  (`live = BLUE`); in every other state it restarts onto the chain already
  live, so it changes nothing.
- `swap.sh rollback-script` prints the pasteable recovery block for whatever
  state the system is in — before or after any operation. It takes no
  arguments, switches nothing, and works when this agent is not running.

### The recovery block, and the pin that proves it was shown

`activate` and `promote` do nothing on their own: they print the recovery block
and a pin, and refuse `--yes` until it is re-run with that pin. The pin is a
hash of the exact block printed for the current state, so it cannot be guessed,
carried over from a different state, or produced without the block first being
printed.

- Run the command bare, then hand the user **the whole block verbatim** — the
  `# ====` lines included, every absolute path as printed, nothing retyped,
  shortened, or paraphrased into prose. It must be a script they can paste when
  this session is gone, so it is never a description of what a command would do.
- Wait for their sign-off, then re-run as `swap.sh <command> --yes <pin>`, where
  `<pin>` is the hash on the block's last line ("Sign-off pin for this state").
  The pin is positional after `--yes`, not a flag.
- A refused pin means the state moved: print the new block, do not force it.

The block restores the bytes that were serving before the operation, so it is
correct in every state without reasoning about which side is live. Pair it with
the Cloudflare fallback (`~/.omp/agent/config.yml` →
`modelRoles.default: cloudflare-gateway/dynamic/fallback2`) for the case where
LiteLLM itself is unreachable. State every path as the full filesystem path the
tool printed — never `swap.sh`, `skill://...`, or `~` shorthand. Never state a
recovery that leaves the live head unrestored.

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

- Agent clients: the `litellm` provider entry and the role pointing at it live
  in the client's own config (`~/.omp/agent/models.yml`, `~/.paseo/config.json`).
- `designer`/`vision` roles and PR-Agent stay on Cloudflare — PR-Agent cannot
  reach localhost.

### Sessions pin their model — restarts never migrate them

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

- Provider-side errors (`DataPolicyError`, region and billing gates) are fixed
  on the provider side, not in this chain's config; while they persist they
  block every live-side command (`Chain members that fail report their provider
  error`). A spent monthly allowance (`MonthlyLimitError`, `GoUsageLimitError`)
  is the exception: it is EXHAUSTED, not a failure, and blocks nothing. Provider
  configuration for these routes is in `skill://cloudflare-ai-gateway`.
- Keys live in `~/.paseo/litellm/env`; never print them.
