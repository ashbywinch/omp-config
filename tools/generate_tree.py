#!/usr/bin/env python3
"""Generate the Notion structure tree markdown.

Mirror-aware: Notion relations are bidirectional, so a parent's Parent Epic /
Parent Value Stream field contains BOTH its own parent AND its children
(mirrors). This script resolves parentage from the child-side links, applies
explicit re-parent overrides, and renders superseded items in their own
section at the bottom.

Usage:
    python3 generate_tree.py [OUTPUT.md]     # default: notion-structure.md in CWD

Requires `ntn` CLI authenticated (see skill://notion-database-management).
Data sources:
    Epics: 20d3122e-1a13-81ee-a750-000ba5e61df5
    Value Streams: 20d3122e-1a13-8180-bf41-000b2f83fdc2
"""

import json
import re
import subprocess
import sys

EPICS_DS = "20d3122e-1a13-81ee-a750-000ba5e61df5"
VS_DS = "20d3122e-1a13-8180-bf41-000b2f83fdc2"

# Explicit re-parents that intentionally break the numbering scheme
# (child number -> parent number). Keep in sync with the org model.
OVERRIDES = {
    "6.1": "6.11", "6.2": "6.11", "6.16": "6.11",
    "6.3": "6.12", "6.10": "6.12",
    "9": "6",
}


def query(ds):
    r = subprocess.run(
        ["ntn", "datasources", "query", ds, "--limit", "100", "--json"],
        capture_output=True, text=True)
    return json.loads(r.stdout).get("results", [])


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

    by_num = {}
    for cid, (p, nm) in em.items():
        n = num(nm)
        if n:
            by_num.setdefault(n, []).append(cid)

    def actual_parent(cid):
        p, nm = em[cid]
        cn = num(nm)
        if cn and ".".join(map(str, cn)) in OVERRIDES:
            pn = tuple(int(x) for x in OVERRIDES[".".join(map(str, cn))].split("."))
            if pn in by_num:
                return by_num[pn][0]
        pe = [x for x in rel(p, "Parent Epic") if x in em and x != cid]
        if not pe:
            return None
        # entries that don't point back at us are the real parent (mirror-aware)
        real = [x for x in pe if cid not in rel(em[x][0], "Parent Epic")]
        if real:
            return real[0]
        if cn:
            best, bestn = None, -1
            for x in pe:
                xn = num(em[x][1])
                if xn and len(xn) < len(cn) and cn[:len(xn)] == xn and len(xn) > bestn:
                    best, bestn = x, len(xn)
            if best:
                return best
        return None

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

    def emit_vs(vid, d=0):
        p, nm = vm[vid]
        ind = "  " * d
        L.append(f"{ind}- **{nm}** ({st(p)})")
        for cv in sorted(vs_kids.get(vid, []), key=lambda v: vm[v][1]):
            emit_vs(cv, d + 1)
        for cid in sorted(vs_epics.get(vid, []), key=lambda c: em[c][1]):
            ep, enm = em[cid]
            L.append(f"{ind}  - {enm} (epic, {st(ep)})")
            for c2 in sorted(kids.get(cid, []), key=lambda c: em[c][1]):
                ep2, enm2 = em[c2]
                L.append(f"{ind}    - {enm2} (epic, {st(ep2)})")

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
