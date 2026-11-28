"""`pr-threads` as a display over the library: the listing and the exit code."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tools.tests.desk_fakes import Fake

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "pr_threads.py"


class ThreadsCommandTest(unittest.TestCase):
    def fake(self, **scenario) -> Fake:
        fake = Fake(**scenario)
        self.addCleanup(fake.close)
        patcher = mock.patch.dict(os.environ, fake.env())
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "1", *args],
            env=os.environ,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_no_unanswered_threads_exits_zero(self):
        self.fake()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 unanswered", result.stdout)

    def test_a_finished_pr_is_named_and_exits_three(self):
        self.fake(state="MERGED", threads=["PRRC_1"])
        result = self.run_cli()
        self.assertEqual(result.returncode, 3)
        self.assertIn("is MERGED — nothing to answer", result.stdout)
        self.assertNotIn("UNANSWERED", result.stdout)

    def test_a_finished_pr_keeps_the_ids_stream_clean(self):
        self.fake(state="CLOSED", threads=["PRRC_1"])
        result = self.run_cli("--ids")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "")
        self.assertIn("is CLOSED — nothing to answer", result.stderr)

    def test_an_unanswered_thread_exits_one_and_names_it(self):
        self.fake(threads=["PRRC_1"])
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("UNANSWERED  f.py:1  @reviewer", result.stdout)

    def test_ids_prints_only_the_ids(self):
        self.fake(threads=["PRRC_2", "PRRC_1"])
        result = self.run_cli("--ids")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.split(), ["PRRC_1", "PRRC_2"])

    def test_ids_with_nothing_pending_exits_zero(self):
        self.fake()
        result = self.run_cli("--ids")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_an_unreadable_read_exits_two(self):
        self.fake(threads_rc=1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("pr-threads:", result.stderr)

    def test_me_from_the_environment_answers_a_thread(self):
        nodes = [{"id": "T1", "isResolved": False, "path": "a.py", "line": 1,
                  "comments": {"nodes": [{"author": {"login": "omp-harness[bot]"}}]}}]
        self.fake(thread_nodes=nodes)
        self.assertEqual(self.run_cli().returncode, 0)

    def test_the_me_flag_overrides_the_default(self):
        nodes = [{"id": "T1", "isResolved": False, "path": "a.py", "line": 1,
                  "comments": {"nodes": [{"author": {"login": "someone"}}]}}]
        self.fake(thread_nodes=nodes)
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.run_cli("--me", "someone").returncode, 0)

    def test_wait_returns_once_the_checks_on_the_head_are_completed(self):
        self.fake()
        result = self.run_cli("--wait")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
