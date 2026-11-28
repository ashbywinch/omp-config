"""The login the CLIs count as mine."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.desk.identity import answering_login


class AnsweringLoginTest(unittest.TestCase):
    def test_the_default_is_the_app_bot(self):
        with mock.patch.dict(os.environ, {"PR_THREADS_ME": ""}):
            self.assertEqual(answering_login(), "omp-harness[bot]")

    def test_the_environment_overrides_it(self):
        with mock.patch.dict(os.environ, {"PR_THREADS_ME": "someone"}):
            self.assertEqual(answering_login(), "someone")

    def test_surrounding_whitespace_is_not_part_of_the_login(self):
        with mock.patch.dict(os.environ, {"PR_THREADS_ME": " me[bot] "}):
            self.assertEqual(answering_login(), "me[bot]")


if __name__ == "__main__":
    unittest.main()
