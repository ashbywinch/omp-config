"""Tests for tools/check_missed_classes.py (stdlib unittest — no deps in this repo).

Run: python3 -m unittest discover -s tools/tests
Wired into `make test` alongside the other self-checks.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_missed_classes import scan  # noqa: E402


def write_module(tmp: Path, name: str, source: str) -> Path:
    p = tmp / name
    p.write_text(source, encoding="utf-8")
    return p


THREE_SHARED = """\
def parse_config(config: Config) -> str:
    return config.raw


def load_config(config: Config) -> Config:
    return config


def save_config(config: Config) -> None:
    config.dirty = True
"""

TWO_SHARED = """\
def parse_config(config: Config) -> str:
    return config.raw


def load_config(config: Config) -> Config:
    return config
"""

DIFFERENT_LEADS = """\
def parse_config(config: Config) -> str:
    return config.raw


def load_record(record: Record) -> Record:
    return record


def save_verdict(verdict: Verdict) -> None:
    verdict.saved = True
"""

METHODS_ONLY = """\
class Config:
    def parse(self) -> str:
        return self.raw

    def load(self) -> "Config":
        return self

    def save(self) -> None:
        self.dirty = True
"""

UNANNOTATED = """\
def parse_config(config) -> str:
    return str(config)


def load_config(config) -> str:
    return str(config)


def save_config(config) -> None:
    pass
"""

MIXED = """\
import json


def parse_config(config: Config) -> str:
    return config.raw


def load_config(config: Config) -> Config:
    return config


def save_config(config: Config) -> None:
    config.dirty = True


def load_record(record: Record) -> Record:
    return record
"""

ASYNC = """\
async def fetch_config(config: Config) -> Config:
    return config


async def refresh_config(config: Config) -> None:
    await config.refresh()


async def save_config(config: Config) -> None:
    config.dirty = True
"""


class MissedClassesScanTest(unittest.TestCase):
    def test_three_shared_params_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            f = write_module(Path(td), "m.py", THREE_SHARED)
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(len(findings), 1)
            self.assertIn("3 free functions", findings[0])
            self.assertIn("'Config'", findings[0])
            self.assertIn(f.name, findings[0])
            self.assertEqual(warnings, [])

    def test_two_shared_params_warns_not_fails(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", TWO_SHARED)
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(findings, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("2 free functions", warnings[0])

    def test_threshold_tunable(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", TWO_SHARED)
            findings, _ = scan([Path(td)], 2)
            self.assertEqual(len(findings), 1)  # two shared params is a finding at threshold 2

    def test_different_leading_params_is_clean(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", DIFFERENT_LEADS)
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(findings, [])
            self.assertEqual(warnings, [])

    def test_class_methods_are_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", METHODS_ONLY)
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(findings, [])
            self.assertEqual(warnings, [])

    def test_unannotated_first_params_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", UNANNOTATED)
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(findings, [])
            self.assertEqual(warnings, [])

    def test_mixed_finds_only_the_missed_class(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", MIXED)
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(len(findings), 1)  # only the Config trio
            self.assertIn("'Config'", findings[0])
            self.assertEqual(warnings, [])

    def test_async_functions_count(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", ASYNC)
            findings, _ = scan([Path(td)], 3)
            self.assertEqual(len(findings), 1)

    def test_directory_walk_and_single_file(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "a.py", THREE_SHARED)
            write_module(Path(td), "b.py", DIFFERENT_LEADS)
            self.assertEqual(len(scan([Path(td)], 3)[0]), 1)
            self.assertEqual(len(scan([Path(td) / "a.py"], 3)[0]), 1)
            self.assertEqual(scan([Path(td) / "b.py"], 3)[0], [])

    def test_broken_source_is_skipped_not_crashed(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "broken.py", "def f(:")
            findings, warnings = scan([Path(td)], 3)
            self.assertEqual(findings, [])
            self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
