#!/usr/bin/env python3
"""Generate the Notion structure tree markdown.

Parentage comes from the child-side link: a page's own `Parent Epic` /
`Parent Value Stream` field holds exactly its parent (dual-property pairs,
see skill://notion-database-management). Superseded items render in their
own section at the bottom.

Usage:
    python3 generate_tree.py [OUTPUT.md]     # default: notion-structure.md in CWD

Requires `ntn` CLI authenticated (see skill://notion-database-management).
Data sources:
    Epics: 20d3122e-1a13-81ee-a750-000ba5e61df5
    Value Streams: 20d3122e-1a13-8180-bf41-000b2f83fdc2
"""

import json
import subprocess
import sys

EPICS_DS = "20d3122e-1a13-81ee-a750-000ba5e61df5"
VS_DS = "20d3122e-1a13-8180-bf41-000b2f83fdc2"


def query(ds):
    r = subprocess.run(
        ["ntn", "datasources", "query", ds, "--limit", "100", "--json"],
        capture_output=True, text=True)
    obj = json.loads(r.stdout)
    if obj.get("has_more"):
        print(f"WARNING: {ds} has more than 100 records — tree may be incomplete",
              file=sys.stderr)
    return obj.get("results", [])


def title(props, key):
    return " ".join(t.get("plain_text", "") for t in (props.get(key) or {}).get("title") or []).strip()


def rel(props, key):
    return [x.get("id") for x in (props.get(key) or {}).get("relation") or []]


def st(p):
    s = (p.get("Status") or {}).get("select")
    return s.get("name") if s else "—"


def num(x):
    m = re.match(r"Epic ([\d.]+)", x)
    return tuple(int(v) for v in m.group(1).split(".")) if m else None


def build():
    epics = query(EPICS_DS)
    vs = query(VS_DS)
    em = {r["id"]: (r.get("properties") or {}, title(r.get("properties") or {}, "Epic Name")) for r in epics}
    vm = {r["id"]: (r.get("properties") or {}, title(r.get("properties") or {}, "Value Stream Name") or "(untitled)") for r in vs}

    def actual_parent(cid):
        # child-side link: own Parent Epic field holds exactly the parent
        p, nm = em[cid]
        pe = [x for x in rel(p, "Parent Epic") if x in em and x != cid]
        return pe[0] if pe else None

    def is_sup(p):
        return st(p) == "Superseded"

    epic_vs = {}
    for cid, (p, nm) in em.items():
        pv = rel(p, "Parent Value Stream")
        if pv:
            epic_vs[cid] = pv[0]
    vs_parent = {}
    for vid, (p, nm) in vm.items():
        pv = rel(p, "Parent Value Stream")
        if pv:
            vs_parent[vid] = pv[0]

    kids = {}
    for cid in em:
        if cid in epic_vs or is_sup(em[cid][0]):
            continue
        pr = actual_parent(cid)
        if pr and not is_sup(em[pr][0]):
            kids.setdefault(pr, []).append(cid)
    vs_kids = {}
    for vid, pid in vs_parent.items():
        if is_sup(vm[vid][0]) or is_sup(vm[pid][0]):
            continue
        vs_kids.setdefault(pid, []).append(vid)
    vs_epics = {}
    for cid, vid in epic_vs.items():
        if is_sup(em[cid][0]) or is_sup(vm[vid][0]):
            continue
        vs_epics.setdefault(vid, []).append(cid)

    L = ["# Notion Structure — Value Streams & Epics", "",
         f"_Generated via tools/generate_tree.py · {len(vs)} value streams · {len(epics)} epics_", "",
         "## Value Streams", ""]

    roots = [vid for vid in vm if vid not in vs_parent and not is_sup(vm[vid][0])]

    def emit_epic(cid, d):
        p, nm = em[cid]
        ind = "  " * d
        L.append(f"{ind}- {nm} (epic, {st(p)})")
        for c2 in sorted(kids.get(cid, []), key=lambda c: em[c][1]):
            emit_epic(c2, d + 1)

    def emit_vs(vid, d=0):
        p, nm = vm[vid]
        ind = "  " * d
        L.append(f"{ind}- **{nm}** ({st(p)})")
        for cv in sorted(vs_kids.get(vid, []), key=lambda v: vm[v][1]):
            emit_vs(cv, d + 1)
        for cid in sorted(vs_epics.get(vid, []), key=lambda c: em[c][1]):
            emit_epic(cid, d + 1)

    for vid in sorted(roots, key=lambda v: vm[v][1]):
        emit_vs(vid)

    L += ["", "## Superseded", ""]
    for cid in sorted([c for c in em if is_sup(em[c][0])], key=lambda c: em[c][1]):
        p, nm = em[cid]
        L.append(f"- **{nm}** (Epic)")
    for vid in sorted([v for v in vm if is_sup(vm[v][0])], key=lambda v: vm[v][1]):
        p, nm = vm[vid]
        L.append(f"- **{nm}** (Value Stream)")

    return "\n".join(L) + "\n"


if __name__ == "__main__":
    out = build()
    path = sys.argv[1] if len(sys.argv) > 1 else "notion-structure.md"
    with open(path, "w") as f:
        f.write(out)
    print(f"written {path}")
