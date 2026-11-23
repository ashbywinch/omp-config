"""The session predicate both shims share: who does this shell belong to?

A shell OpenCode spawns must reach the bot. Paseo sets `PASEO_AGENT_ID` per
*session* (OpenCode's environment), and only for the agent sessions it creates
itself — a subagent is a child session it never sees, so its shells carry
`OPENCODE=1` and no agent id. Without that marker gh fell through to the human's
stored account, and the PR it created could not be approved by that human.

These tests run the real shims against a fake `gh`/`git` on PATH: pass-through
must reach the fake, and every agent marker must stop short of it.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHIMS = {
    "gh": REPO / "tools" / "gh-app-shim",
    "git": REPO / "tools" / "git-app-shim",
    "helper": REPO / "tools" / "omp-bot-credential-helper",
}

AGENT_MARKERS = (
    {"OPENCODE": "1"},
    {"AI_AGENT": "opencode"},
    {"PASEO_AGENT_ID": "agent-123"},
    {"OMP_GIT_IDENTITY": "bot"},
)


class FakeTools:
    """A PATH holding nothing but stand-ins for gh and git."""

    def __init__(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.home = self.root / "home"
        (self.home / ".local" / "etc").mkdir(parents=True)
        (self.home / ".secrets").write_text("", encoding="utf-8")
        for name in ("gh", "git"):
            tool = self.bin / name
            tool.write_text(
                "#!/bin/bash\n"
                'if [ "${1:-}" = "--version" ]; then echo "git version 2.43.0"; exit 0; fi\n'
                f'echo "real-{name} $*"\n',
                encoding="utf-8",
            )
            tool.chmod(0o755)

    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        base = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "LANG": "C.UTF-8",
        }
        base.update(extra or {})
        return base

    def run(self, shim: str, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        args = [str(SHIMS[shim])]
        stdin = ""
        if shim == "helper":
            # git invokes a credential helper as `<helper> get`, request on stdin.
            args.append("get")
            stdin = "protocol=https\nhost=github.com\n\n"
        else:
            args += ["auth", "status"]
        return subprocess.run(
            args,
            env=self.env(extra),
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def close(self) -> None:
        self.dir.cleanup()


class PassThroughTest(unittest.TestCase):
    """A shell with no agent marker is the human's: the real tool runs."""

    def setUp(self) -> None:
        self.tools = FakeTools()
        self.addCleanup(self.tools.close)

    def test_the_human_shell_reaches_the_real_gh(self):
        result = self.tools.run("gh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("real-gh", result.stdout)

    def test_the_human_shell_reaches_the_real_git(self):
        result = self.tools.run("git")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("real-git", result.stdout)

    def test_an_inherited_token_does_not_change_who_decides(self):
        result = self.tools.run("gh", {"GH_TOKEN": "human-token"})
        self.assertIn("real-gh", result.stdout)


class AgentSessionTest(unittest.TestCase):
    """Every marker the launch environment sets takes the shell to the bot.

    Both shims are driven, so a marker dropped from one of them fails here.
    Agent mode needs the app key / agent gitconfig, which this fake HOME does
    not have — so the proof is that the shim stops with its own error instead
    of reaching the real tool with the human's credentials.
    """

    def setUp(self) -> None:
        self.tools = FakeTools()
        self.addCleanup(self.tools.close)

    def test_every_marker_stops_gh_short_of_the_human_account(self):
        for marker in AGENT_MARKERS:
            with self.subTest(marker=marker):
                result = self.tools.run("gh", marker)
                self.assertNotIn("real-gh", result.stdout)
                self.assertNotEqual(result.returncode, 0)

    def test_every_marker_stops_git_short_of_the_human_credentials(self):
        for marker in AGENT_MARKERS:
            with self.subTest(marker=marker):
                result = self.tools.run("git", marker)
                self.assertNotIn("real-git", result.stdout)
                self.assertNotEqual(result.returncode, 0)

    def test_every_marker_makes_the_credential_helper_act(self):
        """A helper that stays silent is a git prompt for the human's password."""
        for marker in AGENT_MARKERS:
            with self.subTest(marker=marker):
                result = self.tools.run("helper", marker)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("password=", result.stdout)

    def test_the_human_shells_helper_stays_silent(self):
        result = self.tools.run("helper")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_agent_mode_says_what_is_missing_rather_than_falling_back(self):
        result = self.tools.run("gh", {"OPENCODE": "1"})
        self.assertIn("GITHUB_APP_ID", result.stderr)


if __name__ == "__main__":
    unittest.main()
