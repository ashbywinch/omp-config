# lucidlint: ignore-file fakefs the tool under test is a shell script — subprocess
# interop with a stubbed binary on PATH needs a REAL filesystem and real exec bits
"""Tests for tools/notion-write.sh (stdlib unittest — no deps in this repo).

The load-bearing contract is the snapshot: a property change must be revertible
to the value that was there before the FIRST write, not to whatever the last
write left behind. The regression this pins is a revert that silently restores
intermediate or reconstructed text — the failure mode that writing a rule
instead of a tool produced.

`ntn` is stubbed on PATH; no network, no Notion workspace.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "notion-write.sh"

NTN_STUB = '''#!{python}
import json, os, sys

if os.environ.get("NOTION_TEST_FAIL"):
    print(os.environ["NOTION_TEST_FAIL"], file=sys.stderr)
    sys.exit(1)

state_path = os.environ["NOTION_TEST_STATE"]
with open(state_path) as fh:
    state = json.load(fh)

args = sys.argv[1:]
page_id = args[1].rsplit("/", 1)[-1]
page = state[page_id]

if "-X" in args and args[args.index("-X") + 1] == "PATCH":
    patch = json.load(sys.stdin)
    for name, body in patch.items():
        kind = next(k for k in body if k != "type")
        page["properties"][name][kind] = body[kind]
        page["properties"][name]["type"] = kind
    with open(state_path, "w") as fh:
        json.dump(state, fh)
    print("{{}}")
else:
    print(json.dumps(page))
'''

ORIGINAL = [{"type": "text", "text": {"content": "Original"}, "plain_text": "Original"}]


class NotionWriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        bindir = self.tmp / "bin"
        bindir.mkdir()
        stub = bindir / "ntn"
        stub.write_text(NTN_STUB.format(python=sys.executable))
        stub.chmod(0o755)

        self.state_file = self.tmp / "state.json"
        self.state_file.write_text(json.dumps({
            "P1": {"properties": {
                "Description": {"type": "rich_text", "rich_text": ORIGINAL},
                "Status": {"type": "select", "select": {"name": "Draft"}},
            }},
        }))

        self.env = dict(
            os.environ,
            PATH=f"{bindir}:{os.environ['PATH']}",
            XDG_STATE_HOME=str(self.tmp / "state"),
            NOTION_TEST_STATE=str(self.state_file),
        )

    def run_tool(self, *args):
        return subprocess.run(
            ["bash", str(TOOL), *args],
            capture_output=True, text=True, env=self.env,
        )

    def write_ok(self, *args):
        """Run a write and require it to succeed — a silent failure would make the
        assertions below pass on a state the tool never wrote."""
        result = self.run_tool(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def value(self, prop="Description", state_file=None):
        data = json.loads((state_file or self.state_file).read_text())
        return data["P1"]["properties"][prop]["rich_text" if prop == "Description" else "select"]

    def snapshot_path(self, prop="Description"):
        return self.tmp / "state" / "notion-snapshots" / "P1" / f"{prop}.json"

    def test_api_failure_is_reported_and_nothing_is_written(self):
        env = dict(self.env, NOTION_TEST_FAIL="connection reset by peer")
        result = subprocess.run(
            ["bash", str(TOOL), "P1", "Description", "--text", "Replaced"],
            capture_output=True, text=True, env=env,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not read page P1", result.stderr)
        self.assertIn("connection reset by peer", result.stderr)
        self.assertEqual(self.value()[0]["text"]["content"], "Original")
        self.assertFalse(self.snapshot_path().exists())

    def test_write_snapshots_the_previous_value(self):
        result = self.run_tool("P1", "Description", "--text", "Replaced")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.value()[0]["text"]["content"], "Replaced")

        snapshot = json.loads(self.snapshot_path().read_text())
        self.assertEqual(snapshot["value"], ORIGINAL)

    def test_revert_restores_the_original_value_exactly(self):
        self.write_ok("P1", "Description", "--text", "Replaced")
        result = self.write_ok("P1", "Description", "--revert")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.value(), ORIGINAL)

    def test_second_write_does_not_replace_the_first_snapshot(self):
        self.write_ok("P1", "Description", "--text", "First")
        self.write_ok("P1", "Description", "--text", "Second")
        self.write_ok("P1", "Description", "--revert")
        self.assertEqual(self.value(), ORIGINAL)

    def test_revert_without_snapshot_refuses_and_leaves_the_page_alone(self):
        result = self.run_tool("P1", "Description", "--revert")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no snapshot", result.stderr)
        self.assertEqual(self.value(), ORIGINAL)

    def test_unknown_property_is_refused(self):
        result = self.run_tool("P1", "Desciption", "--text", "typo")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no property named", result.stderr)

    def test_json_mode_covers_non_rich_text_properties(self):
        result = self.run_tool("P1", "Status", "--json", '{"name": "In Progress"}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.value("Status"), {"name": "In Progress"})


if __name__ == "__main__":
    unittest.main()
