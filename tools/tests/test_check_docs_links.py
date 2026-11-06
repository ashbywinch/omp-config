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
from check_docs_links import _outside_fences  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
