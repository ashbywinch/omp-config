#!/usr/bin/env bash
# Change one Notion page property, snapshotting the previous value first so a
# revert restores what was there rather than a reconstruction of it.
#
# Usage:
#   notion-write.sh <page-id> <property> --text "value"    # rich_text / title
#   notion-write.sh <page-id> <property> --json '<json>'   # any property type
#   notion-write.sh <page-id> <property> --revert          # restore first snapshot
#   notion-write.sh <page-id> <property> --show            # current + snapshot
#
# Snapshots live under ${XDG_STATE_HOME:-$HOME/.local/state}/notion-snapshots/
# <page-id>/<property>.json. The FIRST snapshot for a page+property is kept and
# never overwritten, so --revert always returns to the value from before the
# first write in that store; pass --resnapshot to replace it deliberately.
set -euo pipefail

state_root="${XDG_STATE_HOME:-$HOME/.local/state}"
snapshot_root="$state_root/notion-snapshots"

die() { echo "notion-write: $*" >&2; exit 1; }

command -v ntn >/dev/null || die "ntn not found on PATH"
command -v jq >/dev/null || die "jq not found on PATH"

[ "$#" -ge 3 ] || die "usage: notion-write.sh <page-id> <property> --text|--json|--revert|--show [value]"
page="$1"; prop="$2"; mode="$3"; shift 3

snapshot_dir="$snapshot_root/$page"
snapshot="$snapshot_dir/$(printf '%s' "$prop" | tr '/' '_').json"

# Current state of the property: {"type": "...", "value": ...}. Errors when the
# page has no such property, so a typo cannot patch something else.
read_state() {
  ntn api "v1/pages/$page" | jq -ce --arg p "$prop" '
    .properties[$p] as $o
    | if $o == null then error("no property named \($p)") else {type: $o.type, value: $o[$o.type]} end'
}

apply_state() { # $1 = {"type","value"} JSON, sent as {"<property>": {"<type>": <value>}}
  local body
  body=$(jq -cn --arg p "$prop" --argjson s "$1" '{($p): {($s.type): $s.value}}')
  printf '%s' "$body" | ntn api "v1/pages/$page" -X PATCH >/dev/null
}

show_state() { # $1 = label, $2 = {"type","value"} JSON
  printf '%s: ' "$1"
  jq -r 'if (.value | type) == "array"
         then (.value | map(.plain_text // .text.content // "") | join(""))
         else (.value | tojson) end' <<<"$2"
}

take_snapshot() { # $1 = {"type","value"} JSON
  mkdir -p "$snapshot_dir"
  printf '%s\n' "$1" | jq . > "$snapshot.tmp"
  mv "$snapshot.tmp" "$snapshot"
}

case "$mode" in
  --show)
    show_state "current " "$(read_state)"
    if [ -f "$snapshot" ]; then show_state "snapshot" "$(jq -c . "$snapshot")"
    else echo "snapshot: (none)"; fi
    ;;

  --revert)
    [ -f "$snapshot" ] || die "no snapshot for $page / $prop — nothing to restore; ask what the value should be"
    restored=$(jq -c . "$snapshot")
    show_state "reverting from" "$restored"
    apply_state "$restored"
    show_state "now         " "$(read_state)"
    ;;

  --text)
    [ "$#" -eq 1 ] || die "--text takes exactly one value"
    current=$(read_state)
    type=$(jq -r .type <<<"$current")
    case "$type" in
      rich_text|title) value=$(jq -cn --arg t "$1" '[{type: "text", text: {content: $t}}]') ;;
      *) die "property $prop is $type, not rich_text/title — use --json" ;;
    esac
    [ -f "$snapshot" ] || take_snapshot "$current"
    show_state "before " "$current"
    apply_state "$(jq -cn --arg t "$type" --argjson v "$value" '{type: $t, value: $v}')"
    show_state "after  " "$(read_state)"
    echo "snapshot: $snapshot"
    ;;

  --json)
    [ "$#" -eq 1 ] || die "--json takes exactly one value"
    current=$(read_state)
    type=$(jq -r .type <<<"$current")
    jq -e . >/dev/null <<<"$1" || die "--json value is not valid JSON"
    [ -f "$snapshot" ] || take_snapshot "$current"
    show_state "before " "$current"
    apply_state "$(jq -cn --arg t "$type" --argjson v "$1" '{type: $t, value: $v}')"
    show_state "after  " "$(read_state)"
    echo "snapshot: $snapshot"
    ;;

  --resnapshot)
    take_snapshot "$(read_state)"
    echo "snapshot: $snapshot (replaced)"
    ;;

  *) die "unknown mode $mode (use --text, --json, --revert, --show or --resnapshot)" ;;
esac
