"""Tests for tools/generate_tree.py — the tree builder queries live Notion,
so the tests drive the renderer with synthetic relation data. The contract
under test: an epic nested under an ACTIVE parent appears in the VS tree
ONLY (never also as a Top-Level Epic), superseded items land in the
Superseded section, and an epic under a superseded parent is a root.
"""

import os
import tempfile
import unittest
from pathlib import Path

from tools import generate_tree


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
    return generate_tree._StructureTree(generate_tree._RelationGraph(em, vm)).render()


class EntryPointTest(unittest.TestCase):
    """The script itself runs — the renderer being correct is not enough.

    A refactor removed the argument read and left the writer using an undefined
    name; every unit test still passed, and the script raised NameError on every
    run. This is the test that would have failed.
    """

    # lucidlint: ignore fakefs the entry point's job IS the write; faking open() would test the fake
    def test_writes_the_tree_to_the_path_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "tree.md"
            generate_tree.main([str(target)], render=lambda: "## rendered\n")
            self.assertEqual(target.read_text(), "## rendered\n")

    # lucidlint: ignore fakefs same writer, with the default path
    def test_defaults_the_path_when_no_argument_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = Path.cwd()
            os.chdir(tmp)
            try:
                generate_tree.main([], render=lambda: "## rendered\n")
                self.assertEqual((Path(tmp) / "notion-structure.md").read_text(), "## rendered\n")
            finally:
                os.chdir(before)


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
