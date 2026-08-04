"""Repo self-checks for omp-config (stdlib only — no deps in a config repo).

Two checks, wired into `make test`:

1. **Every relative markdown link resolves** — in README, AGENTS, APPEND_SYSTEM,
   docs/, skills/*/SKILL.md, rules/, profiles/. Skips http(s), #anchors,
   harness URIs (skill://, rule://), template variables, and links inside
   fenced code blocks (the scaffold's .pr_agent.toml template cites repo
   paths in a ```toml fence). A doc that links nowhere is a finding.
2. **Every skill folder has a well-formed SKILL.md** — name frontmatter
   matches the folder, and a description exists (the harness loads skills by
   that name; a mismatch silently breaks skill:// resolution).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^```", re.MULTILINE)
SKIP_PREFIXES = ("http://", "https://", "#", "skill://", "rule://", "agent://", "memory://", "artifact://")


def _doc_files() -> list[Path]:
    files = [p for p in (REPO / "docs").rglob("*.md")] + [p for p in (REPO / "rules").glob("*.md")]
    files += [p for p in (REPO / "skills").rglob("SKILL.md")] + [p for p in (REPO / "profiles").glob("*.md")]
    for name in ("README.md", "AGENTS.md", "APPEND_SYSTEM.md"):
        if (REPO / name).exists():
            files.append(REPO / name)
    return sorted(files)


def _outside_fences(text: str) -> list[tuple[int, int]]:
    """(start, end) spans of the text that are NOT inside ``` fenced blocks."""
    spans: list[tuple[int, int]] = []
    pos = 0
    in_fence = False
    seg_start = 0
    for line in text.splitlines(keepends=True):
        if FENCE_RE.match(line):
            if in_fence:
                spans.append((seg_start, pos))
            else:
                seg_start = pos + len(line)
            in_fence = not in_fence
        pos += len(line)
    if not in_fence:
        spans.append((seg_start, pos))
    return spans


def _check_links() -> list[str]:
    failures: list[str] = []
    for md in _doc_files():
        text = md.read_text(encoding="utf-8")
        spans = _outside_fences(text)
        for span_start, span_end in spans:
            for match in LINK_RE.finditer(text, span_start, span_end):
                url = match.group(2).strip()
                if url.startswith(SKIP_PREFIXES) or "=" in url or " " in url or "{{" in url or "$" in url:
                    continue
                if "#" in url:
                    url = url[: url.index("#")]
                if not url:
                    continue
                target = (md.parent / url).resolve()
                rel = md.relative_to(REPO)
                if not target.is_relative_to(REPO):
                    failures.append(f"{rel}: link '{match.group(1)}' -> {url} (outside repo)")
                elif not target.exists():
                    failures.append(f"{rel}: link '{match.group(1)}' -> {target.relative_to(REPO)} (missing)")
    return failures


def _check_skills() -> list[str]:
    failures: list[str] = []
    for skill_dir in sorted((REPO / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            failures.append(f"skills/{name}: no SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        m = re.match(r"^---\nname:\s*([^\n]+)\n", text)
        if not m:
            failures.append(f"skills/{name}: missing name frontmatter")
        elif m.group(1).strip() != name:
            failures.append(f"skills/{name}: frontmatter name '{m.group(1)}' != folder '{name}'")
        if "description:" not in text.split("---", 2)[1]:
            failures.append(f"skills/{name}: missing description frontmatter")
    return failures


def main() -> int:
    failures = _check_links() + _check_skills()
    if failures:
        print("omp-config self-checks failed:")
        for f in failures:
            print(f"  {f}")
        return 1
    docs = len(_doc_files())
    skills = len(list((REPO / "skills").iterdir()))
    print(f"ok — {docs} docs scanned, {skills} skills well-formed, all relative links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
