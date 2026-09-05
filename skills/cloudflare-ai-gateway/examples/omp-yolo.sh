#!/bin/bash
export OMP_GIT_IDENTITY=bot
# Optional diagnostics (chatty): Bun logs every fetch exchange to stderr —
# enable when troubleshooting truncated streams or socket closes.
# export BUN_CONFIG_VERBOSE_FETCH=true
REPO=$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)
REPO=$(basename "${REPO:-unknown}" 2>/dev/null || echo "unknown")
curl -s -X POST http://localhost:9123/_tag -d "repo=$REPO" 2>/dev/null || true
export OPENAI_BASE_URL="http://localhost:9123/v1"
export OPENAI_API_KEY="$CLOUDFLARE_AIGATEWAY_TOKEN"
ARGS=()
SKIP=false
for arg in "$@"; do
    if $SKIP; then SKIP=false; continue; fi
    if [ "$arg" = "--approval-mode" ]; then SKIP=true; continue; fi
    ARGS+=("$arg")
done
OMP=$(command -v omp 2>/dev/null || echo "$HOME/.bun/bin/omp")
exec "$OMP" "${ARGS[@]}" --approval-mode yolo