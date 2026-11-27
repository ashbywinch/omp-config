# lucidlint: ignore-file fakefs every test here builds a fake bin directory on
# purpose: the subject is which notice the watcher sends, not the filesystem.
"""What the watcher tells the session that owns a PR, and when.

Each test runs the real script in a PATH holding stand-ins for `gh`,
`pr-ready` and `paseo`, one pass at a time (`--once`). The fake `paseo`
records what it was asked to send, so a test asserts on the notice itself
rather than on a log line about it. The harness is `desk_fakes.Fake`.
"""

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tools.tests.desk_fakes import AGENT, Fake

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "pr_desk_watch.py"


def check(name: str, status: str, conclusion: str | None, started: str) -> dict:
    return {"name": name, "status": status, "conclusion": conclusion, "started_at": started}


class NoticeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = self.fake_for()

    def fake_for(self, **scenario) -> Fake:
        fake = Fake(**scenario)
        self.addCleanup(fake.close)
        return fake

    def test_a_failing_required_check_is_reported(self):
        self.fake = self.fake_for(
            required=["self-check"],
            checks=[check("self-check", "completed", "failure", "2026-01-01T00:00:00Z")],
        )
        self.fake.run()
        self.assertIn("failing required check(s)", self.fake.notices())

    def test_a_failing_check_with_an_unknown_required_list_is_not_called_required(self):
        self.fake = self.fake_for(
            contexts_rc=1,
            checks=[check("lint", "completed", "failure", "2026-01-01T00:00:00Z")],
        )
        self.fake.run()
        notices = self.fake.notices()
        self.assertIn("failing check(s)", notices)
        self.assertNotIn("failing required check(s)", notices)

    def test_one_run_per_name_is_kept_and_the_newest_wins(self):
        """A re-run supersedes the run before it; the old failure is not news."""
        self.fake = self.fake_for(
            required=["arm"],
            checks=[
                check("arm", "completed", "failure", "2026-01-01T00:00:00Z"),
                check("arm", "completed", "success", "2026-01-01T00:05:00Z"),
            ],
        )
        self.fake.run()
        self.assertNotIn("failing required check(s)", self.fake.notices())
        self.assertIn("ready for the person's review", self.fake.notices())

    def test_unreadable_checks_hold_readiness(self):
        """An unknown check state is not a clean one."""
        self.fake = self.fake_for(checks_rc=1)
        result = self.fake.run()
        self.assertNotIn("ready for the person's review", self.fake.notices())
        self.assertIn("unreadable", result.stderr)

    def test_a_branch_behind_its_base_is_reported(self):
        self.fake = self.fake_for(merge_state="BEHIND")
        self.fake.run()
        self.assertIn("is behind origin/main", self.fake.notices())

    def test_a_ready_pr_is_reported_with_its_link(self):
        self.fake = self.fake_for()
        self.fake.run()
        notices = self.fake.notices()
        self.assertIn("ready for the person's review", notices)
        self.assertIn("https://github.com/owner/name/pull/1", notices)

    def test_an_approved_clean_pr_is_reported_as_approved_and_clean(self):
        self.fake = self.fake_for(decision="APPROVED")
        self.fake.run()
        self.assertIn("approved and clean", self.fake.notices())

    def test_a_draft_is_not_reported_ready(self):
        self.fake = self.fake_for(draft=True)
        self.fake.run()
        self.assertNotIn("ready for the person's review", self.fake.notices())

    def test_an_unanswered_thread_is_reported_with_the_command(self):
        self.fake = self.fake_for(threads=["PRRC_1", "PRRC_2"])
        self.fake.run()
        notices = self.fake.notices()
        self.assertIn("2 unanswered review thread(s)", notices)
        self.assertIn("pr-threads 1 --repo owner/name", notices)


def load_module():
    """The script as a module, registered so its dataclasses resolve."""
    spec = importlib.util.spec_from_file_location("pr_desk_watch", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NoRepeatTest(unittest.TestCase):
    """A notice is owed once per state, not once per pass."""

    def setUp(self) -> None:
        self.fake = Fake()
        self.addCleanup(self.fake.close)

    def passes(self, count: int) -> str:
        module = load_module()
        with mock.patch.dict(os.environ, self.fake.env()):
            settings = module.Settings(
                pr=1, repo="owner/name", agent=AGENT, interval=1, timeout=5,
                send_timeout=5, root=Path("."),
            )
            watcher = module.Watcher(settings=settings)
            for _ in range(count):
                watcher.pass_once()
        return self.fake.notices()

    def test_a_ready_pr_is_announced_once_across_passes(self):
        notices = self.passes(3)
        self.assertEqual(notices.count("ready for the person's review"), 1)

    def test_a_new_head_is_announced_again(self):
        module = load_module()
        with mock.patch.dict(os.environ, self.fake.env()):
            settings = module.Settings(
                pr=1, repo="owner/name", agent=AGENT, interval=1, timeout=5,
                send_timeout=5, root=Path("."),
            )
            watcher = module.Watcher(settings=settings)
            watcher.pass_once()
            moved = json.loads((self.fake.root / "pr.json").read_text(encoding="utf-8"))
            moved["headRefOid"] = "b" * 40
            (self.fake.root / "pr.json").write_text(json.dumps(moved), encoding="utf-8")
            watcher.pass_once()
        self.assertEqual(self.fake.notices().count("ready for the person's review"), 2)


class RestartTest(unittest.TestCase):
    """The keys live on disk, so a restart does not repeat what was sent."""

    def state_file(self, fake: Fake) -> Path:
        return fake.root / "state" / "omp-config" / "watch" / "owner" / "name" / "1.json"

    def settings(self, module):
        return module.Settings(
            pr=1, repo="owner/name", agent=AGENT, interval=1, timeout=5,
            send_timeout=5, root=Path("."),
        )

    def test_a_second_watcher_sends_no_duplicate(self):
        fake = Fake()
        self.addCleanup(fake.close)
        module = load_module()
        with mock.patch.dict(os.environ, fake.env()):
            module.Watcher(settings=self.settings(module)).pass_once()
            module.Watcher(settings=self.settings(module)).pass_once()
        self.assertEqual(fake.notices().count("ready for the person's review"), 1)

    def test_the_ready_key_is_the_head(self):
        fake = Fake()
        self.addCleanup(fake.close)
        module = load_module()
        with mock.patch.dict(os.environ, fake.env()):
            module.Watcher(settings=self.settings(module)).pass_once()
        keys = json.loads(self.state_file(fake).read_text(encoding="utf-8"))
        self.assertEqual(keys["ready"], "a" * 40)

    def test_a_finished_pr_deletes_its_log(self):
        fake = Fake()
        self.addCleanup(fake.close)
        module = load_module()
        with mock.patch.dict(os.environ, fake.env()):
            watcher = module.Watcher(settings=self.settings(module))
            watcher.pass_once()
            self.assertTrue(self.state_file(fake).exists())
            moved = json.loads((fake.root / "pr.json").read_text(encoding="utf-8"))
            moved["state"] = "MERGED"
            (fake.root / "pr.json").write_text(json.dumps(moved), encoding="utf-8")
            watcher.pass_once()
        self.assertFalse(self.state_file(fake).exists())


class StartupTest(unittest.TestCase):
    def test_the_owner_is_required(self):
        fake = Fake()
        self.addCleanup(fake.close)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "1", "owner/name", "1", "--once"],
            env=fake.env(PR_DESK_AGENT=""),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("PR_DESK_AGENT", result.stderr)

    def test_a_finished_pr_ends_the_watch(self):
        fake = Fake(state="MERGED")
        self.addCleanup(fake.close)
        result = fake.run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("watcher done", result.stdout)
        self.assertEqual(fake.notices(), "")


if __name__ == "__main__":
    unittest.main()
