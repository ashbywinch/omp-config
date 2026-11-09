# lucidlint: ignore-file fakefs these read this repo's real files; faking the
# tree would test the fake, not the repo.
"""The contracts omp-config asserts about itself, as tests.

`tools/check_docs_links.py` holds the walking logic and returns findings; each
test below fails on a non-empty list. This is the gate — `make test` runs the
unittest suite, so a contract that stops being true stops the build.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_docs_links import (  # noqa: E402
    _check_discoverability,
    _check_links,
    _check_skills,
    _check_sizes,
)

REPO = Path(__file__).resolve().parents[2]


class RepoContractsTest(unittest.TestCase):
    def test_every_relative_link_resolves(self):
        self.assertEqual(_check_links(REPO), [])

    def test_every_skill_is_well_formed(self):
        self.assertEqual(_check_skills(REPO), [])

    def test_every_doc_is_discoverable_from_agents_md(self):
        self.assertEqual(_check_discoverability(REPO), [])

    def test_always_loaded_files_are_within_the_ceiling(self):
        self.assertEqual(_check_sizes(REPO).hard, [])

    def test_ci_installs_the_python_the_makefile_builds(self):
        """The interpreter is pinned in two files; they must say one version."""
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        built = re.search(r"^PY_VERSION := (\d+\.\d+)$", makefile, re.MULTILINE)
        installed = re.search(r'python-version: "(\d+\.\d+)"', workflow)
        self.assertIsNotNone(built, "the Makefile no longer states PY_VERSION")
        self.assertIsNotNone(installed, "ci.yml no longer installs a python-version")
        self.assertEqual(built.group(1), installed.group(1),
                         "ci.yml and the Makefile pin different Pythons")

    def test_the_scaffold_example_matches_the_tool(self):
        """tools/ is canonical; the scaffold copy is generated from it."""
        canonical = REPO / "tools" / "check_review_posted.py"
        example = REPO / "skills/new-repo-scaffold/examples/tools/check_review_posted.py"
        self.assertEqual(
            canonical.read_text(encoding="utf-8"),
            example.read_text(encoding="utf-8"),
            "check_review_posted twins diverged — run 'make sync-examples' (tools/ is canonical)",
        )


if __name__ == "__main__":
    unittest.main()
