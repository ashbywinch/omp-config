---
name: archunitpython-glob-rules
description: Use ./ prefix on archunitpython layer globs to avoid fnmatch glob leakage into subdirectories
---

When defining `archunitpython` layer patterns with `defined_by(...)`, always prefix the pattern with `./`.

**Why:** Python's `fnmatch.translate` converts `*` to `.*` (which matches `/`), so a bare `dag/*.py` also matches `tests/unit/dag/anything.py`. The `./` anchors the match to the project root, preventing subdirectory leakage.

This applies to any file that calls `defined_by()` with a path pattern:
- `la.layer("name").defined_by("./path/*.py")` ✓
- `la.layer("name").defined_by("path/*.py")` ✗ — matches subdirectories too
