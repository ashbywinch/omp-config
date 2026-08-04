"""Repo self-checks for omp-config (stdlib only — no deps in a config repo).

Four checks, wired into `make test`:

1. **Every relative markdown link resolves** — in README, AGENTS, APPEND_SYSTEM,
   docs/, skills/*/SKILL.md, rules/, profiles/. Skips http(s), #anchors,
   harness URIs (skill://, rule://), template variables, and links inside
   fenced code blocks (the scaffold's .pr_agent.toml template cites repo
   paths in a ```toml fence). A doc that links nowhere is a finding.
2. **Every skill folder has a well-formed SKILL.md** — name frontmatter
   matches the folder, and a description exists (the harness loads skills by
   that name; a mismatch silently breaks skill:// resolution).
3. **Every doc is discoverable from AGENTS.md** (docs/documentation-structure.md
   rule) — each file in docs/ and rules/ is reachable from AGENTS.md
   directly or one link deep (markdown links and backtick-quoted .md paths).
   An undiscoverable doc is a finding: it does not exist for the reader who
   starts where all readers start.
4. **Always-loaded size ceilings** (docs/writing-documentation.md) — AGENTS.md
   and skill bodies: hard fail above 32 KiB (the stated ceiling), warn above
   200 lines (the target). Skills are documentation; the ceilings apply to
   them like any always-loaded file.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^```", re.MULTILINE)
BACKTICK_PATH_RE = re.compile(r"`([A-Za-z0-9_./*-]+\.md)`")
SKIP_PREFIXES = ("http://", "https://", "#", "skill://", "rule://", "agent://", "memory://", "artifact://")
HARD_BYTES = 32 * 1024
SOFT_LINES = 200


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


def _link_targets(md: Path, text: str) -> list[Path]:
    """Relative markdown-link and backtick-path targets of *md*, resolved."""
    targets: list[Path] = []
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
            if target.is_relative_to(REPO) and target.exists() and target.is_file():
                targets.append(target)
    for match in BACKTICK_PATH_RE.finditer(text):
        raw = match.group(1)
        if "*" in raw:  # a glob reference like rules/*.md — its files are reachable
            for hit in (md.parent).glob(raw):
                if hit.is_file() and hit.is_relative_to(REPO):
                    targets.append(hit.resolve())
            continue
        target = (md.parent / raw).resolve()
        if target.is_relative_to(REPO) and target.exists():
            if target.is_file():
                targets.append(target)
            elif target.is_dir():  # a directory reference — its docs are reachable
                targets.extend(p for p in target.rglob("*.md") if p.is_file())
    return targets


def _check_discoverability() -> list[str]:
    """docs/documentation-structure.md rule: every doc reachable from
    AGENTS.md, directly or one link deep."""
    agents = REPO / "AGENTS.md"
    if not agents.exists():
        return []
    reachable: set[Path] = set()
    frontier = [agents]
    for _depth in range(2):  # AGENTS (0) -> its targets (1) -> their targets (2)
        if not frontier:
            break
        next_frontier: list[Path] = []
        for doc in frontier:
            if doc in reachable:
                continue
            reachable.add(doc)
            text = doc.read_text(encoding="utf-8")
            next_frontier.extend(t for t in _link_targets(doc, text) if t not in reachable)
        frontier = next_frontier
    required = sorted(p for p in _doc_files() if p.is_relative_to(REPO / "docs") or p.is_relative_to(REPO / "rules"))
    return [
        f"{p.relative_to(REPO)}: not reachable from AGENTS.md (directly or one link deep)"
        for p in required
        if p not in reachable
    ]


def _check_sizes() -> tuple[list[str], list[str]]:
    """docs/writing-documentation.md ceilings: hard fail > 32 KiB, warn > 200
    lines, for always-loaded files (AGENTS.md + skill bodies)."""
    files = [REPO / "AGENTS.md" if (REPO / "AGENTS.md").exists() else None]
    files += list((REPO / "skills").rglob("SKILL.md"))
    hard: list[str] = []
    soft: list[str] = []
    for f in files:
        if f is None:
            continue
        text = f.read_text(encoding="utf-8")
        if len(text.encode("utf-8")) > HARD_BYTES:
            hard.append(f"{f.relative_to(REPO)}: {len(text.encode('utf-8'))} bytes > {HARD_BYTES} ceiling")
        elif text.count("\n") > SOFT_LINES:
            soft.append(f"{f.relative_to(REPO)}: {text.count(chr(10))} lines > {SOFT_LINES} target (slim it)")
    return hard, soft


def main() -> int:
    failures = _check_links() + _check_skills() + _check_discoverability()
    hard_sizes, soft_sizes = _check_sizes()
    failures += hard_sizes
    if failures:
        print("omp-config self-checks failed:")
        for f in failures:
            print(f"  {f}")
        return 1
    docs = len(_doc_files())
    skills = len(list((REPO / "skills").iterdir()))
    print(f"ok — {docs} docs scanned, {skills} skills well-formed, links resolve, all docs reachable from AGENTS.md")
    for w in soft_sizes:
        print(f"  warn: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
