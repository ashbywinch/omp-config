# lucidlint: ignore-file fakefs these read this repo's real files; faking the
# tree would test the fake, not the repo.
"""The contracts omp-config asserts about itself, as tests.

`tools/check_docs_links.py` holds the walking logic and returns findings; each
test below fails on a non-empty list. This is the gate — `make test` runs the
unittest suite, so a contract that stops being true stops the build.
"""

import subprocess
import unittest
from pathlib import Path

from tools.check_docs_links import (
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

    def test_no_tracked_file_carries_merge_markers(self):
        """A marker that reached a commit is a merge stopped halfway: the file
        is wrong, and nothing else reads it."""
        result = subprocess.run([str(REPO / "tools" / "check-merge-markers.sh")],
                                capture_output=True, text=True, cwd=REPO)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_the_scaffold_examples_match_their_tools(self):
        """tools/ is canonical; the scaffold copies are generated from it."""
        for name in ("check_review_posted.py", "check-merge-markers.sh"):
            canonical = REPO / "tools" / name
            example = REPO / "skills/new-repo-scaffold/examples/tools" / name
            self.assertEqual(
                canonical.read_text(encoding="utf-8"),
                example.read_text(encoding="utf-8"),
                f"{name} twins diverged — run 'make sync-examples' (tools/ is canonical)",
            )


if __name__ == "__main__":
    unittest.main()
