# lucidlint: ignore-file fakefs every test here builds a fake bin directory on
# purpose: the subject is which notice the watcher sends, not the filesystem.
"""What the watcher tells the session that owns a PR, and when.

Each test runs the real script in a PATH holding stand-ins for `gh`,
`pr-threads`, `pr-ready` and `paseo`, one pass at a time (`--once`). The fake
`paseo` records what it was asked to send, so a test asserts on the notice
itself rather than on a log line about it.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "pr_desk_watch.py"
AGENT = "agent-1"


class Fake:
    """A PATH whose tools answer from one scenario, recording what was sent."""

    def __init__(self, **scenario) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.sent = self.root / "sent.txt"
        self.scenario = scenario
        self.write_tools()

    def close(self) -> None:
        self.dir.cleanup()

    def write_tools(self) -> None:
        pr = {
            "state": self.scenario.get("state", "OPEN"),
            "headRefOid": self.scenario.get("head", "a" * 40),
            "reviewDecision": self.scenario.get("decision", ""),
            "baseRefName": "main",
            "url": "https://github.com/owner/name/pull/1",
            "mergeStateStatus": self.scenario.get("merge_state", "CLEAN"),
        }
        (self.root / "pr.json").write_text(json.dumps(pr), encoding="utf-8")
        checks = self.scenario.get(
            "checks",
            [{"name": "self-check", "status": "completed", "conclusion": "success",
              "started_at": "2026-01-01T00:00:00Z"}],
        )
        (self.root / "checks.json").write_text(
            json.dumps({"check_runs": checks}), encoding="utf-8"
        )
        (self.root / "contexts.json").write_text(
            json.dumps(
                {
                    "data": {
                        "repository": {
                            "ref": {
                                "branchProtectionRule": {
                                    "requiredStatusCheckContexts": self.scenario.get(
                                        "required", []
                                    )
                                }
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.root / "threads.txt").write_text(
            "\n".join(self.scenario.get("threads", [])) + "\n", encoding="utf-8"
        )
        (self.root / "ready.txt").write_text(
            self.scenario.get("ready", "BLOCKED: nothing to report"), encoding="utf-8"
        )
        checks_rc = self.scenario.get("checks_rc", 0)
        ready_rc = self.scenario.get("ready_rc", 1)

        gh = self.bin / "gh"
        gh.write_text(
            "#!/bin/bash\n"
            'root="$FAKE_ROOT"\n'
            'case "$*" in\n'
            '  "pr view"*) cat "$root/pr.json" ;;\n'
            '  *check-runs*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/checks.json" ;;\n'
            '  "api graphql"*) cat "$root/contexts.json" ;;\n'
            '  "api repos"*) echo "[]" ;;\n'
            '  *) echo "unexpected gh call: $*" >&2; exit 9 ;;\n'
            "esac\n" % (checks_rc, checks_rc),
            encoding="utf-8",
        )
        threads = self.bin / "pr-threads"
        threads.write_text(
            '#!/bin/bash\ncat "$FAKE_ROOT/threads.txt"\n', encoding="utf-8"
        )
        ready = self.bin / "pr-ready"
        ready.write_text(
            '#!/bin/bash\ncat "$FAKE_ROOT/ready.txt"\nexit %d\n' % ready_rc,
            encoding="utf-8",
        )
        paseo = self.bin / "paseo"
        paseo.write_text(
            '#!/bin/bash\nprintf "%s\\n" "$3" >> "$FAKE_ROOT/sent.txt"\n',
            encoding="utf-8",
        )
        for tool in (gh, threads, ready, paseo):
            tool.chmod(0o755)

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "FAKE_ROOT": str(self.root),
            "PR_DESK_AGENT": AGENT,
            "PYTHONPATH": str(REPO),
        }
        base.update(extra)
        return base

    def run(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "1", "owner/name", "1", "--once", *extra],
            env=self.env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def notices(self) -> str:
        return self.sent.read_text(encoding="utf-8") if self.sent.exists() else ""


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

    def test_one_run_per_name_is_kept_and_the_newest_wins(self):
        """A re-run supersedes the run before it; the old failure is not news."""
        self.fake = self.fake_for(
            required=["arm"],
            checks=[
                check("arm", "completed", "failure", "2026-01-01T00:00:00Z"),
                check("arm", "completed", "success", "2026-01-01T00:05:00Z"),
            ],
            ready="READY: hand it over",
            ready_rc=0,
        )
        self.fake.run()
        self.assertNotIn("failing required check(s)", self.fake.notices())
        self.assertIn("ready for the person's review", self.fake.notices())

    def test_unreadable_checks_hold_readiness(self):
        """An unknown check state is not a clean one."""
        self.fake = self.fake_for(checks_rc=1, ready="READY: hand it over", ready_rc=0)
        result = self.fake.run()
        self.assertNotIn("ready for the person's review", self.fake.notices())
        self.assertIn("unreadable", result.stderr)

    def test_a_branch_behind_its_base_is_reported(self):
        self.fake = self.fake_for(merge_state="BEHIND")
        self.fake.run()
        self.assertIn("is behind origin/main", self.fake.notices())

    def test_a_ready_pr_is_reported_with_its_link(self):
        self.fake = self.fake_for(ready="READY: hand it over", ready_rc=0)
        self.fake.run()
        notices = self.fake.notices()
        self.assertIn("ready for the person's review", notices)
        self.assertIn("https://github.com/owner/name/pull/1", notices)

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
        self.fake = Fake(ready="READY: hand it over", ready_rc=0)
        self.addCleanup(self.fake.close)

    def passes(self, count: int) -> str:
        module = load_module()
        with mock.patch.dict(os.environ, self.fake.env()):
            settings = module.Settings(
                pr=1, repo="owner/name", agent=AGENT, interval=1, timeout=5,
                send_timeout=5, root=Path("."),
            )
            watcher = module.Watcher(settings=settings, gh=module.Github(settings))
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
            watcher = module.Watcher(settings=settings, gh=module.Github(settings))
            watcher.pass_once()
            moved = json.loads((self.fake.root / "pr.json").read_text(encoding="utf-8"))
            moved["headRefOid"] = "b" * 40
            (self.fake.root / "pr.json").write_text(json.dumps(moved), encoding="utf-8")
            watcher.pass_once()
        self.assertEqual(self.fake.notices().count("ready for the person's review"), 2)


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
