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
from generate_tree import _TreeRenderer  # noqa: E402


def props(**rels):
    return {k: {"relation": [{"id": v}]} for k, v in rels.items()}


EM = {
    "e1": (props(**{"Parent Value Stream": "v1"}), "Alpha"),
    "e2": (props(**{"Parent Epic": "e1"}), "Beta"),
    "e3": ({"Status": {"select": {"name": "Superseded"}}}, "Gamma"),
}
VM = {"v1": ({}, "Stream One"), "v2": ({}, "Stream Two")}


class TreeRendererTest(unittest.TestCase):
    def test_child_of_active_parent_is_nested_not_top_level(self):
        # regression: the kids map is parent -> children; the children (not
        # the keys) are the ones under an active parent
        out = _TreeRenderer(EM, VM).render()
        self.assertIn("    - Beta (epic", out)  # nested under Alpha
        top_level = out.split("## Top-Level Epics", 1)
        self.assertEqual(len(top_level), 1, f"no Top-Level Epics section expected:\n{out}")

    def test_superseded_items_land_in_the_superseded_section(self):
        out = _TreeRenderer(EM, VM).render()
        self.assertIn("## Superseded", out)
        self.assertIn("- **Gamma** (Epic)", out)
        self.assertNotIn("Gamma", out.split("## Superseded", 1)[0])

    def test_epic_under_superseded_parent_is_a_root(self):
        em = {
            "parent": ({"Status": {"select": {"name": "Superseded"}}}, "Parent"),
            "child": (props(**{"Parent Epic": "parent"}), "Child"),
        }
        out = _TreeRenderer(em, {}).render()
        top = out.split("## Top-Level Epics", 1)
        self.assertEqual(len(top), 2)
        self.assertIn("- Child (epic", top[1])


if __name__ == "__main__":
    unittest.main()
