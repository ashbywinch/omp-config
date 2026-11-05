# lucidlint: ignore-file fakefs the dir-walk tests need a REAL directory tree — pyfakefs
# cannot exercise os.walk/link-resolution semantics faithfully
"""Tests for tools/check_docs_links.py (stdlib unittest — no deps in this repo).

The fence-span contract is the load-bearing part of the link check: links
inside ``` code blocks are examples, not navigation, and must be skipped;
links in prose must be scanned. The inversion (scanning fenced content,
dropping prose) would silently validate the wrong text.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_docs_links import (  # noqa: E402
    _missing_refs,
    _outside_fences,
    _skill_ref_names,
)


def spans_of(text: str) -> list[str]:
    return [text[s.start : s.end] for s in _outside_fences(text)]


class OutsideFencesTest(unittest.TestCase):
    def test_prose_around_one_fence(self):
        text = "prose a\n```\nfence content\n```\nprose b\n"
        self.assertEqual(spans_of(text), ["prose a\n", "prose b\n"])

    def test_prose_between_two_fences(self):
        text = "a\n```\nF1\n```\nb\n```\nF2\n```\nc\n"
        self.assertEqual(spans_of(text), ["a\n", "b\n", "c\n"])

    def test_fence_at_start_drops_nothing(self):
        text = "```\nfence only\n```\nprose\n"
        self.assertEqual(spans_of(text), ["prose\n"])

    def test_no_fences_is_whole_text(self):
        text = "just prose\nwith a [link](http://x)\n"
        self.assertEqual(spans_of(text), [text])

    def test_fence_without_close_is_inside(self):
        text = "prose\n```\nnever closed\n"
        self.assertEqual(spans_of(text), ["prose\n"])

    def test_empty_text_has_no_spans(self):
        self.assertEqual(spans_of(""), [])


class SkillRefNamesTest(unittest.TestCase):
    """Which text counts as a skill reference.

    A reference the regex does not match is not 'skipped' — it is invisible, so
    it can never fail. Names with underscores count for that reason.
    """

    def test_plain_reference(self):
        self.assertEqual(_skill_ref_names("see `skill://day-planning`."), ["day-planning"])

    def test_underscore_name_is_matched(self):
        self.assertEqual(_skill_ref_names("`skill://my_skill`"), ["my_skill"])

    def test_placeholder_is_not_a_reference(self):
        self.assertEqual(_skill_ref_names("`skill://<name>` -> skills/<name>/SKILL.md"), [])

    def test_rule_and_agent_uris_are_not_skill_refs(self):
        self.assertEqual(_skill_ref_names("`rule://x` `agent://y`"), [])

    def test_fenced_reference_is_skipped(self):
        text = "prose\n```\nskill://in-a-fence\n```\n`skill://in-prose`\n"
        self.assertEqual(_skill_ref_names(text), ["in-prose"])

    def test_repeats_are_kept_for_the_caller_to_dedupe(self):
        self.assertEqual(_skill_ref_names("`skill://a` `skill://a`"), ["a", "a"])


class MissingRefsTest(unittest.TestCase):
    def test_known_names_are_dropped(self):
        self.assertEqual(_missing_refs(["a", "b"], {"a", "b"}), [])

    def test_unknown_name_is_reported(self):
        self.assertEqual(_missing_refs(["a", "ghost"], {"a"}), ["ghost"])

    def test_each_missing_name_reported_once(self):
        self.assertEqual(_missing_refs(["ghost", "a", "ghost"], {"a"}), ["ghost"])


if __name__ == "__main__":
    unittest.main()
