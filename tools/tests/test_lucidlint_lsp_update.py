# lucidlint: ignore-file fakefs the subject IS the install of a real bundle
# into a fake HOME; faking open() would test the fake, not the updater.
"""The updater installs one release, not a binary inside an older bundle.

A release bundle carries `bin/lucidlint`, `version.txt` and the Python gate.
Replacing only the binary leaves `version.txt` and the gate at the previous
release, so the install reports two versions and runs an old orchestrator
against a new core. Each test drives the real script in a PATH holding a
stand-in `gh` and a fixture asset, then asserts on the installed tree.
"""

import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "lucidlint-lsp-update.sh"
VERSION = "v9.9.9"
ASSET = f"lucidlint-{VERSION}-x86_64-unknown-linux-musl.tar.gz"
BUNDLE = f"lucidlint-{VERSION}-x86_64-unknown-linux-musl"

FAKE_GH = """#!/usr/bin/env bash
set -eu
if [ "$1" = "release" ] && [ "$2" = "download" ]; then
  target=""
  while [ $# -gt 0 ]; do
    case "$1" in
      -D) target="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  cp "$FAKE_ASSET" "$target/"
  exit 0
fi
echo "unexpected gh: $*" >&2
exit 1
"""

FAKE_LUCIDLINT = """#!/usr/bin/env bash
if [ "$1" = "--lsp" ]; then
  cat >/dev/null
  printf 'Content-Length: 120\\r\\n\\r\\n{"jsonrpc":"2.0","id":1,"result":{"version":"9.9.9"}}'
else
  printf 'lucidlint v9.9.9\\n'
fi
"""


class UpdateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.old = self.home / ".local" / "share" / "lucidlint"
        (self.old / "bin").mkdir(parents=True)
        (self.old / "version.txt").write_text("v0.6.9", encoding="utf-8")
        (self.old / "lucidlint.py").write_text("# old orchestrator\n", encoding="utf-8")
        (self.old / "stale.txt").write_text("from the old bundle\n", encoding="utf-8")
        self.write_bin(self.old / "bin" / "lucidlint", "#!/bin/sh\necho 'lucidlint v0.6.9'\n")

        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.write_bin(self.bin / "gh", FAKE_GH)
        self.write_bin(
            self.bin / "uname", "#!/bin/sh\nprintf 'x86_64\\n'\n"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_bin(self, path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def asset(self, version_text: str = VERSION) -> Path:
        bundle = self.root / BUNDLE
        (bundle / "bin").mkdir(parents=True)
        (bundle / "version.txt").write_text(version_text, encoding="utf-8")
        (bundle / "lucidlint.py").write_text("# new orchestrator\n", encoding="utf-8")
        self.write_bin(bundle / "bin" / "lucidlint", FAKE_LUCIDLINT)
        asset = self.root / ASSET
        with tarfile.open(asset, "w:gz") as archive:
            archive.add(bundle, arcname=BUNDLE)
        return asset

    def run_update(self, version_text: str = VERSION) -> subprocess.CompletedProcess[str]:
        env = {
            "HOME": str(self.home),
            "PATH": str(self.bin) + ":/usr/bin:/bin",
            "FAKE_ASSET": str(self.asset(version_text)),
        }
        return subprocess.run(
            ["bash", str(SCRIPT), VERSION],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def installed(self) -> Path:
        return self.home / ".local" / "share" / "lucidlint"

    def test_the_whole_bundle_is_replaced(self) -> None:
        result = self.run_update()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.installed() / "version.txt").read_text(), VERSION)
        self.assertEqual(
            (self.installed() / "lucidlint.py").read_text(), "# new orchestrator\n"
        )
        self.assertFalse((self.installed() / "stale.txt").exists())
        version = subprocess.run(
            [str(self.installed() / "bin" / "lucidlint"), "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(version.stdout, "lucidlint v9.9.9\n")
        self.assertIn('"version":"9.9.9"', result.stdout)

    def test_a_mislabeled_bundle_is_refused(self) -> None:
        result = self.run_update(version_text="v0.6.9")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("v0.6.9", result.stderr)


if __name__ == "__main__":
    unittest.main()
