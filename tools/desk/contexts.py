"""The context names a base branch requires before it merges."""

from __future__ import annotations

import json

from tools.desk.errors import SourceUnknown
from tools.desk.github import Github

class Contexts(Github):
    """Reads the required checks of one base branch."""

    _QUERY = (
        "query($o:String!,$n:String!,$b:String!){repository(owner:$o,name:$n){"
        "ref(qualifiedName:$b){branchProtectionRule{requiredStatusCheckContexts}}}}"
    )

    def required(self, base: str) -> list[str]:
        """Every required context name, sorted; ``SourceUnknown`` when either
        source cannot be read.

        Both sources are read: a partial list would drop a required check, so
        one unreadable source makes the whole answer unknown.
        """
        owner, _, name = self.repo.partition("/")
        reason = f"required contexts unreadable for origin/{base}"
        classic = self.gh(
            [
                "api", "graphql",
                "-f", f"query={self._QUERY}",
                "-f", f"o={owner}", "-f", f"n={name}", "-f", f"b=refs/heads/{base}",
            ],
            reason,
        )
        rules = self.gh(["api", f"repos/{self.repo}/rules/branches/{base}"], reason)
        contexts: set[str] = set()
        try:
            classic_data = json.loads(classic or "{}")
            rule = (
                (classic_data.get("data") or {}).get("repository") or {}
            ).get("ref") or {}
            contexts.update(
                (rule.get("branchProtectionRule") or {}).get(
                    "requiredStatusCheckContexts"
                ) or []
            )
            for entry in json.loads(rules or "[]"):
                if entry.get("type") != "required_status_checks":
                    continue
                for check in (entry.get("parameters") or {}).get(
                    "required_status_checks", []
                ):
                    contexts.add(check.get("context", ""))
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise SourceUnknown(reason) from exc
        return sorted(context for context in contexts if context)
