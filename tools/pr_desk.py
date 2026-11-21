#!/usr/bin/env python3
"""pr-desk — one Paseo workspace, one top-level agent per repo.

    pr-desk ensure <owner/name>   create the desk if absent; ensure its agent
    pr-desk bootstrap             ensure every repo with an open PR
    pr-desk verify                prove the desk has no Google tools

The desk is a separate surface: it reads GitHub only, never Google. It is one
Paseo workspace with one top-level agent per repo, each with its own clone and
worktrees. The agents are created with `paseo run` after removing the caller's
`PASEO_AGENT_ID`, so they are top-level rather than subagents; `pr-desk ensure`
is called by `skill://pr-workflow` when a PR opens.

The clone is made with a sparse checkout that omits `opencode.json`. A clone of
`inbox` would otherwise load this workspace's Google MCP servers and acquire
mail and Drive tools the desk must not have. `pr-desk verify` checks every
clone for that file, and the desk workspace config for any MCP server.

The desk never approves, resolves a thread, or merges. The repo's
`merge-when-approved` workflow merges on the user's approval; a missing or
non-firing workflow is a bug to report, not a reason to merge by hand.
"""
# lucidlint: ignore-file record-shape these dicts are external wire shapes — the
# gh and paseo JSON, the process environment, and the JSON config file. They are
# parsed at the boundary; the domain records are DeskConfig and RepoDesk.
# lucidlint: ignore-file global-state these are the CLI's fixed default paths,
# timeout and static text. Tests patch CONFIG_PATH; the class holds run state.

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

HOME = Path.home()
CONFIG_PATH = HOME / ".config/omp/pr-desk.json"
DESK_DIR = HOME / "Documents/code/pr-desk"
SKILL = Path(__file__).resolve().parent.parent / "skills/pr-workflow/SKILL.md"
COMMAND_TIMEOUT_SECONDS = 300  # clone and API calls; a hung command must return

NO_MCP_CONFIG = {"$schema": "https://opencode.ai/config.json"}
SKILL_NEEDLES = ("pr-desk ensure", "PR_DESK=1", "never approve", "gh pr merge")
ACTIVE_STATUSES = ("idle", "running")
DESK_AGENTS = """# pr-desk

A code-review surface. It reads GitHub only; it has no Google tools.

One top-level agent per repo, labelled `repo:<owner/name>`, each with its own
clone and worktrees. The desk never approves a PR, resolves a review thread, or
merges one: the repo's `merge-when-approved` workflow does that on the user's
approval.
"""


class DeskError(RuntimeError):
    """A command the desk needs failed."""


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def run(args: list[str], *, check: bool = True,
        env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=COMMAND_TIMEOUT_SECONDS, env=env)
    except subprocess.TimeoutExpired as exc:
        raise DeskError("%s timed out" % " ".join(args)) from exc
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise DeskError("%s failed: %s" % (" ".join(args), detail[:500]))
    return proc


def json_command(args: list[str], program: str) -> object:
    proc = run(args)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise DeskError("%s returned no JSON: %s" % (program, exc)) from exc


def paseo_json(args: list[str]) -> object:
    return json_command(["paseo", *args, "--json"], "paseo")


def gh_json(args: list[str]) -> object:
    return json_command(["gh", *args], "gh")


def json_after_banner(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise DeskError("paseo run returned no JSON object: %s"
                        % text.strip()[:200])
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError as exc:
        raise DeskError("paseo run returned invalid JSON: %s" % exc) from exc


def top_level_env() -> dict:
    """The environment for `paseo run` when the caller is an agent.

    Paseo uses `PASEO_AGENT_ID` to make the new agent a subagent and seed it
    with the caller's context. The desk is top-level, so those variables are
    removed for the one call that creates it.
    """
    env = os.environ.copy()
    for key in ("PASEO_AGENT_ID", "PASEO_AGENT_CWD"):
        env.pop(key, None)
    return env


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
@dataclass
class DeskConfig:
    owner: str = "ashbywinch"
    path: str = str(DESK_DIR)
    workspace_id: str | None = None
    provider: str = "opencode"
    model: str = "litellm/primary"
    thinking: str = "default"
    mode: str = "build"

    @classmethod
    def from_dict(cls, data: dict) -> "DeskConfig":
        known = {field.name for field in fields(cls)}
        values = {key: value for key, value in data.items()
                  if key in known and value is not None}
        return cls(**values)

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def desk(self) -> Path:
        return Path(self.path).expanduser()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        CONFIG_PATH.write_text(json.dumps(self.as_dict(), indent=2) + "\n",
                               encoding="utf-8")
        os.chmod(CONFIG_PATH, 0o600)

    @classmethod
    def load(cls) -> "DeskConfig | None":
        if not CONFIG_PATH.is_file():
            return None
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DeskError("%s is not valid JSON: %s"
                            % (CONFIG_PATH, exc)) from exc
        return cls.from_dict(data)

    def write_files(self) -> None:
        desk = self.desk
        desk.mkdir(parents=True, exist_ok=True)
        config_file = desk / "opencode.json"
        if not config_file.exists():
            config_file.write_text(json.dumps(NO_MCP_CONFIG, indent=2) + "\n",
                                   encoding="utf-8")
        agents = desk / "AGENTS.md"
        if not agents.exists():
            agents.write_text(DESK_AGENTS, encoding="utf-8")

    def find_workspace(self) -> str | None:
        desk = self.desk.resolve()
        for workspace in paseo_json(["workspace", "ls"]):
            cwd = str(workspace.get("cwd") or "")
            if cwd and Path(os.path.expanduser(cwd)).resolve() == desk:
                return workspace_id_of(workspace)
        return None

    def workspace_exists(self) -> bool:
        if not self.workspace_id:
            return False
        workspaces = paseo_json(["workspace", "ls"])
        return any(workspace_id_of(workspace) == self.workspace_id
                   for workspace in workspaces)

    def ensure_workspace(self) -> "DeskConfig":
        self.write_files()
        if self.workspace_exists():
            return self
        workspace_id = self.find_workspace()
        if not workspace_id:
            created = paseo_json([
                "workspace", "create",
                "--isolation", "local",
                "--path", str(self.desk),
                "--title", "pr-desk",
            ])
            workspace_id = workspace_id_of(created)
            if not workspace_id:
                raise DeskError("paseo workspace create returned no id")
        self.workspace_id = workspace_id
        self.save()
        return self


def load_config() -> DeskConfig | None:
    return DeskConfig.load()


# --------------------------------------------------------------------------
# workspace
# --------------------------------------------------------------------------
def workspace_id_of(workspace: dict) -> str | None:
    return workspace.get("workspaceId") or workspace.get("id")


# --------------------------------------------------------------------------
# one repo's desk
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class RepoDesk:
    config: DeskConfig
    repo: str

    @property
    def clone(self) -> Path:
        return self.config.desk / "repos" / self.repo

    @property
    def worktrees(self) -> Path:
        return self.config.desk / "worktrees" / self.repo

    def prompt(self) -> str:
        return """You are the PR desk for {repo}. You are a top-level agent in the
pr-desk workspace, one repo per tab. You are not a subagent, and you do not
start another desk. The environment has PR_DESK=1; you are the desk.

Your clone is {clone}. The session cwd is the desk directory; use absolute
paths, or `cd {clone}` in a shell, for git, tests and edits.

The `pr-workflow` helper commands are at `~/.local/bin/pr-threads`,
`~/.local/bin/watch-pr.sh` and `~/.local/bin/fetch-pr-findings.sh`; use the
absolute path if `which` finds nothing. `fetch-run-logs.sh` is at
`~/Documents/code/omp-config/skills/pr-workflow/scripts/fetch-run-logs.sh`.

Read skill://pr-workflow and use it for every PR in {repo}.

Enumerate every open PR:
  gh pr list --repo {repo} --state open --json number,title,isDraft,createdAt,updatedAt,mergeStateStatus,reviewDecision,statusCheckRollup,additions,deletions,labels
Rank them with a reason for the order: age, check state, review state,
unresolved threads, size, labels, mergeability, and whether one blocks another.
Do not use a fixed oldest-first queue.

Work the chosen PR in its own worktree under {worktrees}/pr-<n>; never switch
the clone's main checkout. Drive the author-side loop: read the findings, fix
them, reply to every inline comment with evidence, push once per review pass,
wait for the next review, and repeat.

Never approve a PR, never resolve a review thread, and never merge. The repo's
merge-when-approved workflow merges on the user's approval; if it is absent or
not firing, report that as a bug. Do not run `gh pr merge`.

Re-rank after every merge. Report in this tab: the queue, the chosen PR, and
why. When the queue is empty, say "archive me" and stop.
""".format(repo=self.repo, clone=self.clone, worktrees=self.worktrees)

    def ensure_clone(self) -> Path:
        path = self.clone
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            run(["gh", "repo", "clone", self.repo, str(path)])
        # Remove the repo's opencode.json from the working tree without
        # touching the index: a clone of inbox would otherwise register Google
        # MCP and the desk would acquire mail and Drive tools. Sparse checkout
        # is clean, so `git status` stays empty and the agent cannot commit the
        # removal.
        run(["git", "-C", str(path), "sparse-checkout", "init", "--no-cone"])
        run(["git", "-C", str(path), "sparse-checkout", "set",
             "/*", "!/opencode.json"])
        run(["git", "-C", str(path), "sparse-checkout", "reapply"])
        self.worktrees.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_agent(self) -> str:
        agents = desk_agents(self.repo)
        if agents:
            agent = agents[0]
            if agent.get("status") == "idle":
                run(["paseo", "send", agent["id"],
                     "%s has a new or updated PR. Re-enumerate and rank."
                     % self.repo, "--no-wait"])
                return "woke %s" % agent["id"]
            return "already running: %s" % agent["id"]

        args = [
            "paseo", "run",
            "--workspace", str(self.config.workspace_id),
            "--label", "repo=" + self.repo,
            "--provider", str(self.config.provider),
            "--model", str(self.config.model),
            "--thinking", str(self.config.thinking),
            "--mode", str(self.config.mode),
            "--env", "PR_DESK=1",
            "--env", "PATH=" + os.path.expanduser("~/.local/bin")
            + (os.pathsep + os.environ["PATH"] if os.environ.get("PATH") else ""),
            "--no-wait",
            "--json",
            "--title", ("PR desk: " + self.repo)[:60],
            self.prompt(),
        ]
        created = json_after_banner(run(args, env=top_level_env()).stdout)
        agent_id = created.get("agentId") or created.get("id")
        if not agent_id:
            raise DeskError("paseo run returned no agent id")
        return "created %s" % agent_id


def repo_slug(value: str | None) -> str:
    if value:
        slug = value.strip()
    else:
        proc = run(["git", "remote", "get-url", "origin"], check=False)
        if proc.returncode != 0:
            raise DeskError("no repo given and no origin remote in this directory")
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$",
                          proc.stdout.strip())
        if not match:
            raise DeskError("origin is not a GitHub repository")
        slug = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", slug):
        raise DeskError("%r is not owner/name" % slug)
    return slug


def open_prs(repo: str) -> list[dict]:
    return gh_json(["pr", "list", "--repo", repo, "--state", "open",
                    "--json", "number,title"])


def desk_agents(repo: str) -> list[dict]:
    proc = run(["paseo", "ls", "--global", "--label", "repo=" + repo,
                "--json"], check=False)
    if proc.returncode != 0:
        raise DeskError("paseo ls failed: %s"
                        % (proc.stderr or proc.stdout).strip())
    agents = json.loads(proc.stdout)
    return [agent for agent in agents
            if agent.get("status") in ACTIVE_STATUSES]


def ensure(repo_arg: str | None) -> int:
    repo = repo_slug(repo_arg)
    config = load_config() or DeskConfig()
    config.ensure_workspace()
    prs = open_prs(repo)
    if not prs:
        print("%s: no open PRs; no desk needed" % repo)
        return 0
    desk = RepoDesk(config, repo)
    clone = desk.ensure_clone()
    print("%s: %d open PR(s), clone %s" % (repo, len(prs), clone))
    print("%s: %s" % (repo, desk.ensure_agent()))
    return 0


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------
def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeskError("%s: %s" % (path, exc)) from exc


def has_google_mcp(config: dict) -> bool:
    servers = (config.get("mcp") or {}).get("servers") or {}
    return any("google-workspace" in name for name in servers)


class DeskCheck:
    def __init__(self, config: DeskConfig):
        self.config = config
        self.failures: list[str] = []

    def workspace(self) -> None:
        if not self.config.workspace_exists():
            self.failures.append("desk workspace %r is not active"
                                 % self.config.workspace_id)
        desk_file = self.config.desk / "opencode.json"
        if not desk_file.is_file():
            self.failures.append("desk has no opencode.json")
        elif has_google_mcp(read_json(desk_file)):
            self.failures.append("desk opencode.json registers a Google MCP server")

    def clone(self, clone: Path) -> None:
        repos = self.config.desk / "repos"
        repo = clone.relative_to(repos).as_posix()
        config_file = clone / "opencode.json"
        if config_file.exists():
            if has_google_mcp(read_json(config_file)):
                self.failures.append(
                    "%s: opencode.json registers a Google MCP server" % repo)
            else:
                self.failures.append(
                    "%s: opencode.json is present; the clone is not isolated"
                    % repo)
        tracked = run(["git", "-C", str(clone), "ls-tree", "-r", "--name-only",
                       "HEAD", "--", "opencode.json"], check=False)
        if tracked.returncode == 0 and tracked.stdout.strip():
            if config_file.exists():
                self.failures.append(
                    "%s: tracked opencode.json is in the working tree" % repo)
            sparse = clone / ".git" / "info" / "sparse-checkout"
            if not sparse.is_file() or "opencode.json" not in sparse.read_text(
                    encoding="utf-8", errors="replace"):
                self.failures.append(
                    "%s: sparse checkout does not exclude opencode.json" % repo)
        workflow = clone / ".github" / "workflows"
        if not any((workflow / name).is_file() for name in
                   ("automerge.yml", "pr-automerge.yml")):
            self.failures.append(
                "%s: no auto-merge workflow — a bug to report" % repo)

    def skill(self) -> None:
        if not SKILL.is_file():
            self.failures.append("pr-workflow skill is not at %s" % SKILL)
            return
        text = SKILL.read_text(encoding="utf-8")
        missing = [needle for needle in SKILL_NEEDLES if needle not in text]
        self.failures.extend("pr-workflow does not state %r" % needle
                             for needle in missing)

    def agents(self) -> None:
        repos_dir = self.config.desk / "repos"
        if not repos_dir.is_dir():
            return
        desk = str(self.config.desk)
        labeled: set[str] = set()
        for clone in sorted(repos_dir.glob("*/*")):
            if not clone.is_dir():
                continue
            repo = clone.relative_to(repos_dir).as_posix()
            agents = desk_agents(repo)
            if len(agents) > 1:
                self.failures.append("%s has %d active desk agents: %s"
                                     % (repo, len(agents),
                                        ", ".join(str(a.get("id")) for a in agents)))
            for agent in agents:
                labeled.add(str(agent.get("id")))
                cwd = os.path.expanduser(str(agent.get("cwd") or ""))
                if not cwd.startswith(desk):
                    self.failures.append(
                        "%s: agent %s is outside the desk (%s)"
                        % (repo, agent.get("id"), cwd))
        for agent in paseo_json(["ls", "--global", "--json"]):
            cwd = os.path.expanduser(str(agent.get("cwd") or ""))
            if agent.get("status") not in ACTIVE_STATUSES \
                    or not cwd.startswith(desk):
                continue
            if str(agent.get("id")) not in labeled:
                self.failures.append("desk agent %s has no repo label"
                                     % agent.get("id"))

    def run(self) -> int:
        try:
            self.workspace()
            repos = self.config.desk / "repos"
            if repos.is_dir():
                for clone in sorted(repos.glob("*/*")):
                    if clone.is_dir():
                        self.clone(clone)
            self.skill()
            self.agents()
        except DeskError as exc:  # lucidlint: ignore swallow the failure is recorded in self.failures and returned as the exit status
            self.failures.append(str(exc))
        for failure in self.failures:
            print("FAIL  " + failure)
        print()
        print("%d failure(s)" % len(self.failures))
        return 1 if self.failures else 0


def verify() -> int:
    config = load_config()
    if config is None:
        print("NOTE  no desk configured at %s — nothing to verify" % CONFIG_PATH)
        return 0
    return DeskCheck(config).run()


# --------------------------------------------------------------------------
# bootstrap and command line
# --------------------------------------------------------------------------
def bootstrap(owner: str | None) -> int:
    config = load_config() or DeskConfig()
    owner = owner or config.owner
    search = gh_json(["search", "prs", "--owner", owner, "--state", "open",
                      "--limit", "100", "--json", "repository"])
    repos = sorted({item["repository"]["nameWithOwner"] for item in search})
    if not repos:
        print("no open PRs under %s" % owner)
        return 0
    failures = 0
    for repo in repos:
        try:
            ensure(repo)
        except DeskError as exc:
            failures += 1
            print("FAIL  %s: %s" % (repo, exc), file=sys.stderr)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="One pr-desk workspace, one top-level agent per repo.")
    sub = parser.add_subparsers(dest="command", required=True)
    ensure_cmd = sub.add_parser("ensure", help="ensure a desk agent for a repo")
    ensure_cmd.add_argument("repo", nargs="?", help="owner/name; default: origin")
    bootstrap_cmd = sub.add_parser("bootstrap",
                                   help="ensure every repo with an open PR")
    bootstrap_cmd.add_argument("--owner",
                               help="GitHub owner (default: ashbywinch)")
    sub.add_parser("verify", help="prove the desk has no Google tools")
    args = parser.parse_args(argv)

    try:
        if args.command == "ensure":
            return ensure(args.repo)
        if args.command == "bootstrap":
            return bootstrap(args.owner)
        if args.command == "verify":
            return verify()
    except DeskError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
