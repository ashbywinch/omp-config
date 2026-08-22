# lucidlint: ignore-file record-shape the synthetic fixtures are the wire shape
# the renderer consumes — a class per fixture would obscure the relation data
"""Tests for tools/generate_tree.py — the tree builder queries live Notion,
so the tests drive the renderer with synthetic relation data. The contract
under test: an epic nested under an ACTIVE parent appears in the VS tree
ONLY (never also as a Top-Level Epic), superseded items land in the
Superseded section, and an epic under a superseded parent is a root.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import generate_tree  # noqa: E402  (sys.path bootstrap must precede the import)


def page(props, name):
    return generate_tree._Page(props, name)


def props(**rels):
    return {k: {"relation": [{"id": v}]} for k, v in rels.items()}


EM = {
    "e1": page(props(**{"Parent Value Stream": "v1"}), "Alpha"),
    "e2": page(props(**{"Parent Epic": "e1"}), "Beta"),
    "e3": page({"Status": {"select": {"name": "Superseded"}}}, "Gamma"),
}
VM = {"v1": page({}, "Stream One"), "v2": page({}, "Stream Two")}


def render(em, vm):
    return generate_tree._TreeRenderer(generate_tree._RelationGraph(em, vm)).render()


class TreeRendererTest(unittest.TestCase):
    def test_child_of_active_parent_is_nested_not_top_level(self):
        # regression: the kids map is parent -> children; the children (not
        # the keys) are the ones under an active parent
        out = render(EM, VM)
        self.assertIn("    - Beta (epic", out)  # nested under Alpha
        top_level = out.split("## Top-Level Epics", 1)
        self.assertEqual(len(top_level), 1, f"no Top-Level Epics section expected:\n{out}")

    def test_superseded_items_land_in_the_superseded_section(self):
        out = render(EM, VM)
        self.assertIn("## Superseded", out)
        self.assertIn("- **Gamma** (Epic)", out)
        self.assertNotIn("Gamma", out.split("## Superseded", 1)[0])

    def test_epic_under_superseded_parent_is_a_root(self):
        em = {
            "parent": page({"Status": {"select": {"name": "Superseded"}}}, "Parent"),
            "child": page(props(**{"Parent Epic": "parent"}), "Child"),
        }
        out = render(em, {})
        top = out.split("## Top-Level Epics", 1)
        self.assertEqual(len(top), 2)
        self.assertIn("- Child (epic", top[1])


if __name__ == "__main__":
    unittest.main()
