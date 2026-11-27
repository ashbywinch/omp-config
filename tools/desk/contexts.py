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
        # A 404 here is not "no rules": the endpoint answers an empty array when
        # nothing applies, so any failure is an unreadable source. One unreadable
        # source makes the answer unknown, because a partial required list would
        # let a required check be missed.
        contexts: set[str] = set()
        try:
            classic_data = _body(classic, reason)
            rule = (
                (classic_data.get("data") or {}).get("repository") or {}
            ).get("ref") or {}
            contexts.update(
                (rule.get("branchProtectionRule") or {}).get(
                    "requiredStatusCheckContexts"
                ) or []
            )
            rules_data = _body(rules, reason)
            if not isinstance(rules_data, list):
                # "No rules" is an empty array; any other body is not an answer.
                raise SourceUnknown(reason)
            for entry in rules_data:
                if entry.get("type") != "required_status_checks":
                    continue
                for check in (entry.get("parameters") or {}).get(
                    "required_status_checks", []
                ):
                    contexts.add(check.get("context", ""))
        except (AttributeError, TypeError) as exc:
            raise SourceUnknown(reason) from exc
        return sorted(context for context in contexts if context)


def _body(text: str, reason: str) -> object:
    """One response body, parsed.

    A blank body is not "nothing applies": `gh` exits zero with output when it
    has an answer, so a body we cannot parse in either direction is a source we
    could not read, and that makes the whole required list unknown.
    """
    if not text.strip():
        raise SourceUnknown(reason)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceUnknown(reason) from exc
