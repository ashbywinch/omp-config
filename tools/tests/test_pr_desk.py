"""Tests for the PR desk tool.

The rules pinned here are the ones that make the desk a separate surface: a
clone cannot carry the repo's `opencode.json` (which registers Google MCP), the
agent is top-level in the desk workspace with a repo label, an existing idle
agent is woken rather than duplicated, and the desk never merges.

    python3 -m unittest discover -s tools/tests -t .
"""
# lucidlint: ignore-file fakefs these tests assert the config's 0600 mode, the
# clone/worktree paths and the sparse-checkout command; the filesystem is the
# subject, not a stand-in.

import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pr_desk", HERE.parent / "pr_desk.py")
pr_desk = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pr_desk
SPEC.loader.exec_module(pr_desk)


def proc(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def config(tmp):
    return pr_desk.DeskConfig(
        owner="ashbywinch",
        path=str(pathlib.Path(tmp) / "desk"),
        workspace_id="wks_test",
        provider="opencode",
        model="litellm/primary",
        thinking="default",
        mode="build",
    )


class RepoSlug(unittest.TestCase):
    def test_owner_name_is_accepted(self):
        self.assertEqual(pr_desk.repo_slug("ashbywinch/inbox"),
                         "ashbywinch/inbox")

    def test_a_bare_name_is_refused(self):
        with self.assertRaises(pr_desk.DeskError):
            pr_desk.repo_slug("inbox")

    def test_origin_url_is_read(self):
        with mock.patch.object(
                pr_desk, "run",
                return_value=proc("git@github.com:ashbywinch/inbox.git\n")):
            self.assertEqual(pr_desk.repo_slug(None), "ashbywinch/inbox")

    def test_a_non_github_origin_is_refused(self):
        with mock.patch.object(
                pr_desk, "run",
                return_value=proc("git@gitlab.com:ashbywinch/inbox.git\n")):
            with self.assertRaises(pr_desk.DeskError):
                pr_desk.repo_slug(None)


class Config(unittest.TestCase):
    def test_a_round_trip_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "omp" / "pr-desk.json"
            with mock.patch.object(pr_desk, "CONFIG_PATH", path):
                cfg = config(tmp)
                cfg.save()
                self.assertEqual(pr_desk.DeskConfig.load(), cfg)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_missing_config_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                    pr_desk, "CONFIG_PATH", pathlib.Path(tmp) / "none.json"):
                self.assertIsNone(pr_desk.DeskConfig.load())

    def test_the_workspace_id_field_is_workspace_id(self):
        with mock.patch.object(
                pr_desk, "paseo_json",
                return_value=[{"workspaceId": "wks_one"}]):
            self.assertTrue(
                pr_desk.DeskConfig(workspace_id="wks_one").workspace_exists())
            self.assertFalse(
                pr_desk.DeskConfig(workspace_id="wks_two").workspace_exists())

    def test_an_existing_desk_workspace_is_reused_by_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config(tmp)
            with mock.patch.object(
                    pr_desk, "paseo_json",
                    return_value=[{"workspaceId": "wks_found",
                                   "cwd": cfg.path}]):
                self.assertEqual(cfg.find_workspace(), "wks_found")


class Prompt(unittest.TestCase):
    def test_it_names_the_repo_the_clone_and_the_merge_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = pr_desk.RepoDesk(config(tmp), "ashbywinch/inbox").prompt()
        self.assertIn("ashbywinch/inbox", text)
        self.assertIn("never merge", text.replace("Never merge", "never merge"))
        self.assertIn("worktrees", text)
        self.assertIn("PR_DESK=1", text)
        self.assertIn("repos/ashbywinch/inbox", text)
        self.assertIn("~/.local/bin/pr-threads", text)


class Clone(unittest.TestCase):
    def test_the_clone_omits_opencode_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config(tmp)
            calls = []

            def fake_run(args, check=True):
                calls.append(args)
                return proc()

            with mock.patch.object(pr_desk, "run", side_effect=fake_run):
                path = pr_desk.RepoDesk(cfg, "ashbywinch/inbox").ensure_clone()
            self.assertEqual(calls[0][:4], ["gh", "repo", "clone",
                                            "ashbywinch/inbox"])
            sparse = [c for c in calls if "sparse-checkout" in c]
            self.assertTrue(sparse)
            self.assertIn("!/opencode.json", sparse[-1])
            self.assertTrue((pathlib.Path(cfg.path) / "worktrees"
                             / "ashbywinch/inbox").is_dir())


class Agents(unittest.TestCase):
    def test_a_running_agent_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            desk = pr_desk.RepoDesk(config(tmp), "ashbywinch/inbox")
            with mock.patch.object(
                    pr_desk, "desk_agents",
                    return_value=[{"id": "agent", "status": "running"}]):
                with mock.patch.object(pr_desk, "run") as run:
                    out = desk.ensure_agent()
            self.assertIn("already running", out)
            run.assert_not_called()

    def test_an_idle_agent_is_woken(self):
        with tempfile.TemporaryDirectory() as tmp:
            desk = pr_desk.RepoDesk(config(tmp), "ashbywinch/inbox")
            with mock.patch.object(
                    pr_desk, "desk_agents",
                    return_value=[{"id": "agent", "status": "idle"}]):
                with mock.patch.object(pr_desk, "run") as run:
                    desk.ensure_agent()
            self.assertEqual(run.call_args.args[0][:3],
                             ["paseo", "send", "agent"])
            self.assertIn("--no-wait", run.call_args.args[0])

    def test_a_new_agent_is_top_level_in_the_desk_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config(tmp)
            with mock.patch.object(pr_desk, "desk_agents", return_value=[]):
                with mock.patch.object(
                        pr_desk, "run",
                        return_value=proc('{"agentId": "agent-1"}')) as run:
                    out = pr_desk.RepoDesk(
                        cfg, "ashbywinch/inbox").ensure_agent()
            args = run.call_args.args[0]
            self.assertIn("--workspace", args)
            self.assertEqual(args[args.index("--workspace") + 1], "wks_test")
            self.assertIn("--env", args)
            self.assertEqual(args[args.index("--env") + 1], "PR_DESK=1")
            self.assertIn("repo=ashbywinch/inbox", args)
            self.assertIn("--no-wait", args)
            self.assertIn("--json", args)
            self.assertNotIn("PASEO_AGENT_ID", run.call_args.kwargs["env"])
            self.assertIn("created agent-1", out)


class Ensure(unittest.TestCase):
    def test_a_repo_with_no_prs_does_not_create_the_desk(self):
        with mock.patch.object(pr_desk, "repo_slug",
                               return_value="ashbywinch/inbox"), \
             mock.patch.object(pr_desk, "open_prs", return_value=[]), \
             mock.patch.object(pr_desk.DeskConfig, "ensure_workspace") as workspace:
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(pr_desk.ensure("ashbywinch/inbox"), 0)
        workspace.assert_not_called()
        self.assertIn("no open PRs", out.getvalue())


class Verify(unittest.TestCase):
    def test_no_config_is_not_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(
                    pr_desk, "CONFIG_PATH", pathlib.Path(tmp) / "none.json"):
                self.assertEqual(pr_desk.verify(), 0)

    def test_a_desk_config_with_google_mcp_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = config(tmp)
            desk = pathlib.Path(cfg.path)
            desk.mkdir(parents=True)
            (desk / "opencode.json").write_text(json.dumps({
                "mcp": {"servers": {"google-workspace": {}}}
            }))
            with mock.patch.object(pr_desk, "CONFIG_PATH",
                                   pathlib.Path(tmp) / "pr-desk.json"), \
                 mock.patch.object(pr_desk, "load_config", return_value=cfg), \
                 mock.patch.object(pr_desk.DeskConfig, "workspace_exists",
                                   return_value=True), \
                 mock.patch.object(pr_desk.DeskCheck, "skill"), \
                 mock.patch.object(pr_desk.DeskCheck, "agents"):
                out = io.StringIO()
                with redirect_stdout(out):
                    code = pr_desk.verify()
            self.assertEqual(code, 1)
            self.assertIn("Google MCP", out.getvalue())

    def test_google_mcp_detection(self):
        self.assertTrue(pr_desk.has_google_mcp({
            "mcp": {"servers": {"google-workspace-paul": {}}}}))
        self.assertFalse(pr_desk.has_google_mcp({"mcp": {"servers": {}}}))
        self.assertFalse(pr_desk.has_google_mcp({}))


if __name__ == "__main__":
    unittest.main()
