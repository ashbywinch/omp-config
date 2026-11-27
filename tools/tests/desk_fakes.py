# lucidlint: ignore-file fakefs every test using this harness builds a fake bin
# directory on purpose: the subject is what a tool says, not the filesystem.
"""A PATH whose tools answer from one scenario, recording what was sent.

The fake `gh` serves the payloads the readers parse — a pull request, its check
runs, its required contexts and branch rules, its review threads, and this
checkout's name. The fake `paseo` records the notices the watcher sends. Every
scenario key has a default, so a test states only the fact it is about.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT = "agent-1"


def _thread_nodes(ids: list[str]) -> list[dict]:
    """One unanswered review thread per id, last spoken by someone else."""
    return [
        {
            "id": thread_id,
            "isResolved": False,
            "path": "f.py",
            "line": 1,
            "comments": {
                "nodes": [{"author": {"login": "reviewer"}, "body": "found"}],
            },
        }
        for thread_id in ids
    ]


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
            "baseRefName": self.scenario.get("base", "main"),
            "url": "https://github.com/owner/name/pull/1",
            "mergeStateStatus": self.scenario.get("merge_state", "CLEAN"),
            "isDraft": self.scenario.get("draft", False),
        }
        if self.scenario.get("omit_draft"):
            del pr["isDraft"]
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
        (self.root / "rules.json").write_text(
            json.dumps(self.scenario.get("rules", [])), encoding="utf-8"
        )
        thread_nodes = self.scenario.get(
            "thread_nodes", _thread_nodes(self.scenario.get("threads", []))
        )
        (self.root / "threads.json").write_text(
            json.dumps(
                {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "reviewThreads": {
                                    "pageInfo": {
                                        "hasNextPage": False,
                                        "endCursor": None,
                                    },
                                    "nodes": thread_nodes,
                                }
                            }
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.root / "repo.json").write_text(
            json.dumps({"nameWithOwner": "owner/name"}), encoding="utf-8"
        )
        checks_rc = self.scenario.get("checks_rc", 0)
        pull_rc = self.scenario.get("pull_rc", 0)
        contexts_rc = self.scenario.get("contexts_rc", 0)
        rules_rc = self.scenario.get("rules_rc", 0)
        repo_rc = self.scenario.get("repo_rc", 0)
        threads_rc = self.scenario.get("threads_rc", 0)

        gh = self.bin / "gh"
        gh.write_text(
            "#!/bin/bash\n"
            'root="$FAKE_ROOT"\n'
            'case "$*" in\n'
            '  "pr view"*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/pr.json" ;;\n'
            '  *check-runs*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/checks.json" ;;\n'
            '  *reviewThreads*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/threads.json" ;;\n'
            '  "api graphql"*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/contexts.json" ;;\n'
            '  "api repos"*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/rules.json" ;;\n'
            '  "repo view"*) if [ %d -ne 0 ]; then exit %d; fi; cat "$root/repo.json" ;;\n'
            '  *) echo "unexpected gh call: $*" >&2; exit 9 ;;\n'
            "esac\n"
            % (pull_rc, pull_rc, checks_rc, checks_rc, threads_rc, threads_rc,
               contexts_rc, contexts_rc, rules_rc, rules_rc, repo_rc, repo_rc),
            encoding="utf-8",
        )
        paseo = self.bin / "paseo"
        paseo.write_text(
            "#!/bin/bash\n"
            "# A send without --no-wait waits for the recipient's turn, and a slow\n"
            "# turn reads as a failed send: refuse it so the tests pin the flag.\n"
            'case "$*" in\n'
            "  *--no-wait*) ;;\n"
            '  *) echo "paseo send was not given --no-wait" >&2; exit 2 ;;\n'
            "esac\n"
            'printf "%s\\n" "${@: -1}" >> "$FAKE_ROOT/sent.txt"\n',
            encoding="utf-8",
        )
        for tool in (gh, paseo):
            tool.chmod(0o755)

    def env(self, **extra: str) -> dict[str, str]:
        base = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "FAKE_ROOT": str(self.root),
            "PR_DESK_AGENT": AGENT,
            "PYTHONPATH": str(REPO),
            # Each test owns its notice state: a shared state directory would
            # let one test's keys suppress another's notice.
            "XDG_STATE_HOME": str(self.root / "state"),
        }
        base.update(extra)
        return base

    def run(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(REPO / "tools" / "pr_desk_watch.py"),
             "1", "owner/name", "1", "--once", *extra],
            env=self.env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def notices(self) -> str:
        return self.sent.read_text(encoding="utf-8") if self.sent.exists() else ""
