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
    if r.returncode != 0:
        sys.exit(f"ntn query failed for {ds}: {r.stderr.strip()}")
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


def _is_sup(p):
    return st(p) == "Superseded"


def _sorted_by_name(ids, table):
    """ids ordered by their name in *table* — one sort-key lambda instead of
    one at every call site."""
    return sorted(ids, key=lambda c: table[c][1])


def _epic_relations(em):
    """Epic-side maps: epic_vs (epic -> VS) and kids (epic -> active child
    epics). actual_parent is closure-local — only the kids computation needs
    the child-side link resolution."""

    def actual_parent(cid):
        # child-side link: own Parent Epic field holds exactly the parent
        p, nm = em[cid]
        pe = [x for x in rel(p, "Parent Epic") if x in em and x != cid]
        return pe[0] if pe else None

    epic_vs = {}
    for cid, (p, nm) in em.items():
        pv = rel(p, "Parent Value Stream")
        if pv:
            epic_vs[cid] = pv[0]
    kids = {}
    for cid in em:
        if cid in epic_vs or _is_sup(em[cid][0]):
            continue
        pr = actual_parent(cid)
        # child of an active parent -> nested; child of a superseded/missing
        # parent -> root (never silently omitted)
        if pr and not _is_sup(em[pr][0]):
            kids.setdefault(pr, []).append(cid)
    return epic_vs, kids


def _vs_relations(vm, epic_vs, em):
    """VS-side maps: vs_parent, vs_kids, vs_epics (dangling relations are
    left out rather than crashed on)."""
    vs_parent = {}
    for vid, (p, nm) in vm.items():
        pv = rel(p, "Parent Value Stream")
        if pv:
            vs_parent[vid] = pv[0]
    vs_kids = {}
    for vid, pid in vs_parent.items():
        if vid not in vm or pid not in vm:
            continue  # dangling relation — leave it out rather than crash
        if _is_sup(vm[vid][0]) or _is_sup(vm[pid][0]):
            continue
        vs_kids.setdefault(pid, []).append(vid)
    vs_epics = {}
    for cid, vid in epic_vs.items():
        if vid not in vm:
            continue  # dangling relation — leave it out rather than crash
        if _is_sup(em[cid][0]) or _is_sup(vm[vid][0]):
            continue
        vs_epics.setdefault(vid, []).append(cid)
    return vs_parent, vs_kids, vs_epics


def _superseded_lines(em, vm):
    """The Superseded section bullet lines, name-ordered."""
    lines = []
    for cid in _sorted_by_name([c for c in em if _is_sup(em[c][0])], em):
        p, nm = em[cid]
        lines.append(f"- **{nm}** (Epic)")
    for vid in _sorted_by_name([v for v in vm if _is_sup(vm[v][0])], vm):
        p, nm = vm[vid]
        lines.append(f"- **{nm}** (Value Stream)")
    return lines


class _TreeRenderer:
    """Renders the structure tree markdown. The emit walkers are
    mutual-recursive methods over the relation maps, sharing the line
    buffer — the shape lucidlint's latent-class rule surfaces as a class
    in disguise, so it IS a class."""

    def __init__(self, em, vm):
        self.em = em
        self.vm = vm
        self.lines = []
        epic_vs, kids = _epic_relations(em)
        vs_parent, vs_kids, vs_epics = _vs_relations(vm, epic_vs, em)
        self.epic_vs = epic_vs
        self.kids = kids
        self.vs_parent = vs_parent
        self.vs_kids = vs_kids
        self.vs_epics = vs_epics

    def _emit_epic(self, cid, d):
        p, nm = self.em[cid]
        ind = "  " * d
        self.lines.append(f"{ind}- {nm} (epic, {st(p)})")
        for c2 in _sorted_by_name(self.kids.get(cid, []), self.em):
            self._emit_epic(c2, d + 1)

    def _emit_vs(self, vid, d=0):
        p, nm = self.vm[vid]
        ind = "  " * d
        self.lines.append(f"{ind}- **{nm}** ({st(p)})")
        for cv in _sorted_by_name(self.vs_kids.get(vid, []), self.vm):
            self._emit_vs(cv, d + 1)
        for cid in _sorted_by_name(self.vs_epics.get(vid, []), self.em):
            self._emit_epic(cid, d + 1)

    def render(self):
        """The full markdown: header, the VS tree with nested epics,
        top-level epics, then the superseded section."""
        em, vm = self.em, self.vm
        self.lines += ["# Notion Structure — Value Streams & Epics", "",
                       f"_Generated via tools/generate_tree.py · {len(vm)} value streams · {len(em)} epics_", "",
                       "## Value Streams", ""]

        roots = [vid for vid in vm if vid not in self.vs_parent and not _is_sup(vm[vid][0])]
        # active epics not under a VS and not under an active epic parent: roots
        # (covers children whose parent was superseded, and any genuinely
        # top-level epic). "kids" maps a parent to its children — the
        # CHILDREN are the ones with an active parent.
        active_children = {c for cs in self.kids.values() for c in cs}
        epic_roots = [cid for cid in em
                      if cid not in self.epic_vs and not _is_sup(em[cid][0])
                      and cid not in active_children]

        for vid in _sorted_by_name(roots, vm):
            self._emit_vs(vid)
        if epic_roots:
            self.lines += ["", "## Top-Level Epics", ""]
            for cid in _sorted_by_name(epic_roots, em):
                self._emit_epic(cid, 0)

        self.lines += ["", "## Superseded", ""] + _superseded_lines(em, vm)
        return "\n".join(self.lines) + "\n"


def build():
    epics = query(EPICS_DS)
    vs = query(VS_DS)
    em = {r["id"]: (r.get("properties") or {}, title(r.get("properties") or {}, "Epic Name")) for r in epics}
    vm = {r["id"]: (r.get("properties") or {}, title(r.get("properties") or {}, "Value Stream Name") or "(untitled)") for r in vs}
    return _TreeRenderer(em, vm).render()





if __name__ == "__main__":
    out = build()
    path = sys.argv[1] if len(sys.argv) > 1 else "notion-structure.md"
    with open(path, "w") as f:
        f.write(out)
    print(f"written {path}")
