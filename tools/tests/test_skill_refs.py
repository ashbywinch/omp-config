# lucidlint: ignore-file fakefs the contract test reads this repo's real markdown;
# faking the tree would test the fake, not the repo.
"""A `skill://` reference must resolve to a skill in this repo.

A skill that ships with one project is not part of this repo: naming it works
only while that project is the open workspace, and silently resolves to nothing
everywhere else. The contract test walks every doc `make test` already scans and
fails on a name that has no `skills/<name>/SKILL.md` here.
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_docs_links import _doc_files, _outside_fences  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SKILL_REF_RE = re.compile(r"skill://([a-z0-9][a-z0-9_-]*)")


def skill_ref_names(text: str) -> list[str]:
    """Every `skill://name` in *text*, outside fenced blocks."""
    names: list[str] = []
    for fence in _outside_fences(text):
        names.extend(m.group(1) for m in SKILL_REF_RE.finditer(text, fence.start, fence.end))
    return names


def missing_refs(names: list[str], known: set[str]) -> list[str]:
    """Referenced names not in *known*, deduped, in order."""
    missing: list[str] = []
    for name in names:
        if name not in known and name not in missing:
            missing.append(name)
    return missing


class SkillRefNamesTest(unittest.TestCase):
    """Which text counts as a reference.

    A name the regex does not match is not skipped — it is invisible, so it can
    never fail. Underscored names count for that reason.
    """

    def test_plain_reference(self):
        self.assertEqual(skill_ref_names("see `skill://day-planning`."), ["day-planning"])

    def test_underscore_name_is_matched(self):
        self.assertEqual(skill_ref_names("`skill://my_skill`"), ["my_skill"])

    def test_placeholder_is_not_a_reference(self):
        self.assertEqual(skill_ref_names("`skill://<name>` -> skills/<name>/SKILL.md"), [])

    def test_other_harness_uris_are_not_skill_refs(self):
        self.assertEqual(skill_ref_names("`rule://x` `agent://y`"), [])

    def test_fenced_reference_is_skipped(self):
        text = "prose\n```\nskill://in-a-fence\n```\n`skill://in-prose`\n"
        self.assertEqual(skill_ref_names(text), ["in-prose"])

    def test_repeats_are_kept_for_the_caller_to_dedupe(self):
        self.assertEqual(skill_ref_names("`skill://a` `skill://a`"), ["a", "a"])


class MissingRefsTest(unittest.TestCase):
    def test_known_names_are_dropped(self):
        self.assertEqual(missing_refs(["a", "b"], {"a", "b"}), [])

    def test_unknown_name_is_reported(self):
        self.assertEqual(missing_refs(["a", "ghost"], {"a"}), ["ghost"])

    def test_each_missing_name_reported_once(self):
        self.assertEqual(missing_refs(["ghost", "a", "ghost"], {"a"}), ["ghost"])


class ThisRepoTest(unittest.TestCase):
    def test_every_skill_reference_resolves_here(self):
        known = {p.parent.name for p in (REPO / "skills").glob("*/SKILL.md")}
        broken: list[str] = []
        for md in _doc_files():
            for name in missing_refs(skill_ref_names(md.read_text(encoding="utf-8")), known):
                broken.append(f"{md.relative_to(REPO)}: skill://{name}")
        self.assertEqual(broken, [], "references to skills that are not in this repo")


if __name__ == "__main__":
    unittest.main()
