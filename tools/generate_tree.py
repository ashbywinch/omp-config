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
from typing import NamedTuple

EPICS_DS = "20d3122e-1a13-81ee-a750-000ba5e61df5"
VS_DS = "20d3122e-1a13-8180-bf41-000b2f83fdc2"


def query(ds):
    r = subprocess.run(
        ["ntn", "query", ds],
        capture_output=True, text=True)
    obj = json.loads(r.stdout)
    return obj.get("results", [])


def title(props, key):
    return " ".join(t.get("plain_text", "") for t in (props.get(key) or {}).get("title") or []).strip()


def rel(props, key):
    return [x.get("id") for x in (props.get(key) or {}).get("relation") or []]


def _sorted_by_name(ids, table):
    """ids ordered by their name in *table* — one sort-key lambda instead of
    one at every call site."""
    return sorted(ids, key=lambda c: table[c].name)


class _Page(NamedTuple):
    """A Notion page entry: its raw properties and its display name."""

    props: dict
    name: str

    @property
    def status(self):
        s = (self.props.get("Status") or {}).get("select")
        return s.get("name") if s else "—"

    def is_superseded(self):
        return self.status == "Superseded"


class _RelationGraph:
    """The workspace hierarchy: the page tables plus the parent/child maps.
    Built once from the raw queries, queried by the renderer."""

    def __init__(self, em, vm):
        self.em = em
        self.vm = vm
        epic_vs, kids = self._epic_relations()
        vs_parent, vs_kids, vs_epics = self._vs_relations(epic_vs)
        self.epic_vs = epic_vs
        self.kids = kids
        self.vs_parent = vs_parent
        self.vs_kids = vs_kids
        self.vs_epics = vs_epics

    def _actual_parent(self, cid):
        # child-side link: own Parent Epic field holds exactly the parent
        pe = [x for x in rel(self.em[cid].props, "Parent Epic") if x in self.em and x != cid]
        return pe[0] if pe else None

    def _epic_relations(self):
        """Epic-side maps: epic_vs (epic -> VS) and kids (epic -> active
        child epics)."""
        epic_vs = {}
        for cid, page in self.em.items():
            pv = rel(page.props, "Parent Value Stream")
            if pv:
                epic_vs[cid] = pv[0]
        kids = {}
        for cid in self.em:
            if cid in epic_vs or self.em[cid].is_superseded():
                continue
            pr = self._actual_parent(cid)
            # child of an active parent -> nested; child of a superseded/missing
            # parent -> root (never silently omitted)
            if pr and not self.em[pr].is_superseded():
                kids.setdefault(pr, []).append(cid)
        return epic_vs, kids

    def _vs_relations(self, epic_vs):
        """VS-side maps: vs_parent, vs_kids, vs_epics (dangling relations are
        left out rather than crashed on)."""
        vs_parent = {}
        for vid, page in self.vm.items():
            pv = rel(page.props, "Parent Value Stream")
            if pv:
                vs_parent[vid] = pv[0]
        vs_kids = self._group_active(vs_parent.items(), self.vm, self.vm)
        vs_epics = self._group_active(epic_vs.items(), self.em, self.vm)
        return vs_parent, vs_kids, vs_epics

    @staticmethod
    def _group_active(pairs, first_table, second_table):
        """children grouped by parent — a child whose table entry is missing
        or superseded (a dangling relation) is left out rather than crashed
        on."""
        grouped = {}
        for child, parent in pairs:
            if not (
                child in first_table
                and parent in second_table
                and not first_table[child].is_superseded()
                and not second_table[parent].is_superseded()
            ):
                continue
            grouped.setdefault(parent, []).append(child)
        return grouped


class _TreeRenderer:
    """Renders the structure tree markdown. The emit walkers are
    mutual-recursive methods over the graph, sharing the line buffer."""

    def __init__(self, graph):
        self.graph = graph
        self.lines = []

    def _emit_epic(self, cid, d):
        page = self.graph.em[cid]
        ind = "  " * d
        self.lines.append(f"{ind}- {page.name} (epic, {page.status})")
        for c2 in _sorted_by_name(self.graph.kids.get(cid, []), self.graph.em):
            self._emit_epic(c2, d + 1)

    def _emit_vs(self, vid, d=0):
        page = self.graph.vm[vid]
        ind = "  " * d
        self.lines.append(f"{ind}- **{page.name}** ({page.status})")
        for cv in _sorted_by_name(self.graph.vs_kids.get(vid, []), self.graph.vm):
            self._emit_vs(cv, d + 1)
        for cid in _sorted_by_name(self.graph.vs_epics.get(vid, []), self.graph.em):
            self._emit_epic(cid, d + 1)

    def _superseded_lines(self):
        """The Superseded section bullet lines, name-ordered."""
        em, vm = self.graph.em, self.graph.vm
        epic_lines = [
            f"- **{em[cid].name}** (Epic)"
            for cid in _sorted_by_name([c for c in em if em[c].is_superseded()], em)
        ]
        vs_lines = [
            f"- **{vm[vid].name}** (Value Stream)"
            for vid in _sorted_by_name([v for v in vm if vm[v].is_superseded()], vm)
        ]
        return epic_lines + vs_lines

    def render(self):
        """The full markdown: header, the VS tree with nested epics,
        top-level epics, then the superseded section."""
        graph = self.graph
        em, vm = graph.em, graph.vm
        self.lines += ["# Notion Structure — Value Streams & Epics", "",
                       f"_Generated via tools/generate_tree.py · {len(vm)} value streams · {len(em)} epics_", "",
                       "## Value Streams", ""]

        roots = [vid for vid in vm if vid not in graph.vs_parent and not vm[vid].is_superseded()]
        # active epics not under a VS and not under an active epic parent: roots
        # (covers children whose parent was superseded, and any genuinely
        # top-level epic). "kids" maps a parent to its children — the
        # CHILDREN are the ones with an active parent.
        active_children = {c for cs in graph.kids.values() for c in cs}
        epic_roots = [cid for cid in em
                      if cid not in graph.epic_vs and not em[cid].is_superseded()
                      and cid not in active_children]

        for vid in _sorted_by_name(roots, vm):
            self._emit_vs(vid)
        if epic_roots:
            self.lines += ["", "## Top-Level Epics", ""]
            for cid in _sorted_by_name(epic_roots, em):
                self._emit_epic(cid, 0)

        self.lines += ["", "## Superseded", ""] + self._superseded_lines()
        return "\n".join(self.lines) + "\n"


def build():
    epics = query(EPICS_DS)
    vs = query(VS_DS)
    em = {r["id"]: _Page(r.get("properties") or {}, title(r.get("properties") or {}, "Epic Name")) for r in epics}
    vm = {r["id"]: _Page(r.get("properties") or {}, title(r.get("properties") or {}, "Value Stream Name") or "(untitled)") for r in vs}
    return _TreeRenderer(_RelationGraph(em, vm)).render()


if __name__ == "__main__":
    out = build()
    path = sys.argv[1] if len(sys.argv) > 1 else "notion-structure.md"
    with open(path, "w") as f:
        f.write(out)
    print(f"written {path}")
