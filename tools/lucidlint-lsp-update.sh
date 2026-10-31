#!/usr/bin/env bash
# lucidlint-lsp-update.sh — install a lucidlint release as the LSP server that
# editors and agents spawn, then prove the version it serves.
#
#   lucidlint-lsp-update.sh            # latest release
#   lucidlint-lsp-update.sh v0.6.9     # pin a release
#
# Replaces ~/.local/share/lucidlint/bin/lucidlint, kills the clients still
# serving the old rules, and prints what a stdio initialize handshake answers.
set -euo pipefail

REPO=ashbywinch/lucidlint
BIN_DIR="$HOME/.local/share/lucidlint/bin"
BIN="$BIN_DIR/lucidlint"

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh (GitHub CLI) is required to fetch a lucidlint release" >&2
  exit 1
fi

VER="${1:-$(gh release view --repo "$REPO" --json tagName -q .tagName)}"

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) ASSET="lucidlint-$VER-x86_64-unknown-linux-musl.tar.gz" ;;
  *) echo "error: no lucidlint release asset for architecture $ARCH" >&2; exit 1 ;;
esac

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

gh release download "$VER" --repo "$REPO" -p "$ASSET" -D "$TMP"
tar xzf "$TMP/$ASSET" -C "$TMP"
mkdir -p "$BIN_DIR"

# Locate the binary instead of deriving the top-level directory from the asset
# name: the archive owns its own layout.
BIN_SRC="$(find "$TMP" -type f -path '*/bin/lucidlint' -print -quit)"
if [ -z "$BIN_SRC" ]; then
  echo "error: no bin/lucidlint inside $ASSET" >&2
  exit 1
fi
install -m 755 "$BIN_SRC" "$BIN"

# Running clients keep serving the old rules until they exit; the next request
# respawns them from the replaced binary. Match the exact command line so the
# kill cannot reach a shell or a different tool.
# No match is success: nothing is serving the old rules.
pgrep -af '/lucidlint/bin/lucidlint --lsp$' | awk '{print $1}' | xargs -r kill || true

# A minimal but spec-shaped initialize: processId, rootUri and capabilities are
# required members, and a server may reject or hang on an empty params object.
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":null,"capabilities":{}}}'
SERVED="$(printf 'Content-Length: %d\r\nContent-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n%s' \
  "$(printf '%s' "$INIT" | wc -c | tr -d ' ')" "$INIT" \
  | timeout 3 "$BIN" --lsp | grep -o '"version":"[^"]*"' || true)"

echo "installed: $BIN ($VER)"
if [ -z "$SERVED" ]; then
  echo "served:    none — the server did not answer the handshake" >&2
  exit 1
fi
echo "served:    $SERVED"
