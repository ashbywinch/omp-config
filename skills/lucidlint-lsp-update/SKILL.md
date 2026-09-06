---
name: lucidlint-lsp-update
description: |
  Updating the installed lucidlint LSP server — download the release
  bundle, replace the binary, restart running clients, verify the SERVED
  version with a handshake. Read when asked to update, upgrade, or install
  the lucidlint LSP.
---

# lucidlint LSP update

lucidlint (github.com/ashbywinch/lucidlint) is both a gate and an LSP
server: the same binary runs `lucidlint --lsp` over stdio. The installed
server the editors and omp agents use lives at
`~/.local/share/lucidlint/bin/lucidlint` — an old binary there keeps
serving old rules until replaced AND its running clients are killed.

## Update in one pass

```sh
VER=$(gh release view --repo ashbywinch/lucidlint --json tagName -q .tagName)
             # ^ latest release; pin one instead (VER=v0.5.0) to repeat an install
gh release download $VER --repo ashbywinch/lucidlint \
  -p "lucidlint-$VER-x86_64-unknown-linux-musl.tar.gz"
tar xzf "lucidlint-$VER-x86_64-unknown-linux-musl.tar.gz"
install -m 755 "lucidlint-$VER-x86_64-unknown-linux-musl/bin/lucidlint" \
  ~/.local/share/lucidlint/bin/lucidlint
pkill -f 'lucidlint --lsp'   # clients keep serving the old rules until
                             # killed; the editor/omp respawns on demand
```

## Verify what is SERVED, not just that a file moved

A stdio `initialize` handshake answers with the server's own version:

```sh
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
printf 'Content-Length: %d\r\n\r\n%s' "${#INIT}" "$INIT" \
  | timeout 3 ~/.local/share/lucidlint/bin/lucidlint --lsp \
  | grep -o '"version":"[^"]*"'
# expect the installed release, e.g. "version":"v0.5.0"
```

## Gotchas (each cost a real session)

- **`~/.local/bin/lucid-lint` (hyphenated) is a different tool** — a
  prose-accessibility linter. It is not lucidlint; do not update,
  replace, or measure it. A `grep -ri lucid` sweep hits it; read its
  `--help` before treating anything as lucidlint.
- **Running clients survive a binary swap** — kill them after replacing
  (`pkill -f 'lucidlint --lsp'`); omp respawns on the next request. Check
  for strays: `pgrep -fa 'lucidlint --lsp'` (a day-old client was found
  serving 0.4.0 at ~40% memory).
- **Gate staleness is a separate guard**: the orchestrator refuses a
  local build older than the scanner sources (`make scanner-check`) —
  that guard protects pytest/the gate; this skill protects the installed
  LSP.
