# lucidlint: ignore-file fakefs the subject is a real state file: atomic rename,
# mtime-based pruning and the XDG fallback are filesystem semantics, so a fake
# filesystem would test the fake.
"""The notice log: where it lives, what it stores, and what it forgets."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tools.desk.noticelog import NoticeLog


class PathTest(unittest.TestCase):
    def test_the_path_follows_xdg_state_home(self):
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": "/state"}):
            log = NoticeLog.for_pr("owner/name", 7)
        self.assertEqual(
            log.path, Path("/state/omp-config/watch/owner/name/7.json")
        )

    def test_the_path_falls_back_to_local_state(self):
        with mock.patch.dict(
            os.environ, {"XDG_STATE_HOME": "", "HOME": "/home/person"}
        ):
            log = NoticeLog.for_pr("owner/name", 7)
        self.assertEqual(
            log.path,
            Path("/home/person/.local/state/omp-config/watch/owner/name/7.json"),
        )


class StoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "watch" / "1.json"

    def test_keys_round_trip_exactly_through_a_new_instance(self):
        log = NoticeLog(self.path)
        log.set("threads", "T2\nT1")
        log.set("checks", "a" * 40 + " self-check")
        reopened = NoticeLog(self.path)
        self.assertEqual(reopened.get("threads"), "T2\nT1")
        self.assertEqual(reopened.get("checks"), "a" * 40 + " self-check")

    def test_an_unset_key_is_owed(self):
        self.assertEqual(NoticeLog(self.path).get("ready"), "")

    def test_a_missing_file_is_all_owed(self):
        self.assertEqual(NoticeLog(self.path).get("threads"), "")

    def test_a_corrupt_file_is_owed_not_a_crash(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{not json", encoding="utf-8")
        self.assertEqual(NoticeLog(self.path).get("ready"), "")

    def test_delete_removes_the_file(self):
        log = NoticeLog(self.path)
        log.set("ready", "a" * 40)
        log.delete()
        self.assertFalse(self.path.exists())

    def test_a_write_leaves_no_temporary_file(self):
        log = NoticeLog(self.path)
        log.set("ready", "a" * 40)
        self.assertEqual(
            sorted(p.name for p in self.path.parent.iterdir()), ["1.json"]
        )
        self.assertEqual(json.loads(self.path.read_text())["ready"], "a" * 40)

    def test_clearing_a_key_is_written(self):
        log = NoticeLog(self.path)
        log.set("ready", "a" * 40)
        log.set("ready", "")
        self.assertEqual(NoticeLog(self.path).get("ready"), "")


class PruneTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name) / "watch"

    def make(self, name: str, age_days: float) -> Path:
        path = self.root / "owner" / "name" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        stamp = time.time() - age_days * 24 * 60 * 60
        os.utime(path, (stamp, stamp))
        return path

    def test_a_file_older_than_seven_days_is_removed(self):
        stale = self.make("1.json", age_days=8)
        self.assertEqual(NoticeLog.prune(self.root), [stale])
        self.assertFalse(stale.exists())

    def test_a_young_file_is_kept(self):
        young = self.make("2.json", age_days=6)
        self.assertEqual(NoticeLog.prune(self.root), [])
        self.assertTrue(young.exists())

    def test_a_future_dated_file_is_removed(self):
        future = self.make("3.json", age_days=-30)
        self.assertEqual(NoticeLog.prune(self.root), [future])
        self.assertFalse(future.exists())

    def test_an_abandoned_temporary_file_is_removed(self):
        temporary = self.make(".1.json.abc.tmp", age_days=8)
        self.assertEqual(NoticeLog.prune(self.root), [temporary])
        self.assertFalse(temporary.exists())

    def test_a_young_temporary_file_is_removed_too(self):
        temporary = self.make(".1.json.abc.tmp", age_days=0)
        self.assertEqual(NoticeLog.prune(self.root), [temporary])
        self.assertFalse(temporary.exists())

    def test_a_missing_root_prunes_nothing(self):
        self.assertEqual(NoticeLog.prune(self.root / "absent"), [])


if __name__ == "__main__":
    unittest.main()
