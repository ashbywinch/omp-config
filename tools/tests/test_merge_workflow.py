# lucidlint: ignore-file fakefs this reads the repo's real workflow file.
"""The merge gate's contract, asserted on the workflow file."""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "merge-when-approved.yml"


class MergeWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_the_branch_is_updated_in_one_place(self):
        self.assertEqual(self.text.count('update-branch"'), 1)

    def test_the_required_check_is_dispatched_in_one_place(self):
        self.assertEqual(self.text.count("gh workflow run"), 1)

    def test_the_dispatch_names_the_workflow_once(self):
        self.assertEqual(self.text.count("CI_WORKFLOW=ci.yml"), 1)

    def test_the_update_path_reports_failure(self):
        start = self.text.index("update_and_dispatch()")
        body = self.text[start:self.text.index("count_threads()")]
        self.assertGreaterEqual(body.count("return 1"), 2)
        self.assertEqual(body.count("::error::"), 2)

    def test_the_app_token_is_used_when_it_exists(self):
        self.assertIn("create-github-app-token", self.text)
        self.assertIn("steps.app-token.outputs.token || secrets.GITHUB_TOKEN", self.text)


if __name__ == "__main__":
    unittest.main()
