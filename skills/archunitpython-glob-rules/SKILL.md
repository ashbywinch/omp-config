---
name: archunitpython-glob-rules
description: archunitpython layer patterns are matched against ABSOLUTE paths — derive them from the project root; relative/./ globs match nothing and make the check pass vacuously
---

When defining `archunitpython` layer patterns with `defined_by(...)`, use
**absolute patterns derived from the project root at runtime**. Never use
`./`-prefixed relative globs.

**Why:** `archunitpython` matches layer patterns against ABSOLUTE
normalized file paths (e.g. `/home/user/proj/dag/expression.py`), not
paths relative to the project. `fnmatch.translate("./dag/*.py")` compiles
to a regex anchored on `./` — which no absolute path starts with — so
**the layer matches zero files, every edge resolves to no layer, and the
assertion passes vacuously**. This bug is silent: the test is green while
enforcing nothing. (Real case: `dag/expression.py` imported
`houses.stamp_duty` for months with a "working" layer test.)

**Correct pattern** — derive the root and use absolute globs:

```python
from pathlib import Path

ROOT = str(Path(__file__).resolve().parents[3])  # repo root — count parents to the repo dir!

la = project_layers()
la = la.layer("dag").defined_by(f"{ROOT}/dag/*.py")
la = la.layer("houses").defined_by(f"{ROOT}/houses/*.py")  # fnmatch * crosses "/" — whole tree
```

**fnmatch semantics that matter here:**
- `*` crosses `/` (`fnmatch.translate` → `.*`), so `{ROOT}/houses/*.py`
  matches every `.py` file under `houses/` recursively — no `**` needed.
- `**/*.py` does NOT match top-level files (`**` then a literal `/`), so
  `{ROOT}/houses/**/*.py` misses `houses/stamp_duty.py`.
- The old "subdirectory leakage" fear (a `dag/*.py` glob also matching
  `tests/unit/dag/…`) does not apply to absolute patterns: the paths are
  distinct and the regex is anchored at the root. Define separate layers
  (`dag` vs `dag_tests`) with their own absolute roots.

**Sanity rule:** after configuring layers, verify the check is real —
introduce a known violation (or run with a temporary bad import) and
confirm the test goes red. A green architecture test that has never seen
a violation is enforcing nothing.
