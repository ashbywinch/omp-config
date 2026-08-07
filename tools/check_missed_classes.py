"""Function-strewing check — "function strewing is a missed class".

Detects the pattern from docs/coding-standards.md: module-level functions
that share the same leading parameter are methods on a class that has not
been written yet. When three or more free functions take the same first
parameter, the class is a finding; two is the prompt to consolidate.

Stdlib-only (this is a config repo — no deps). Parses with the `ast`
module, walks paths, reports findings, exits nonzero on any.

    python3 tools/check_missed_classes.py [paths...] [--threshold N]
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_THRESHOLD = 3


def _first_param_annotation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """The annotation of the function's first parameter, as source text.

    Returns None when there is no first parameter or it is unannotated
    (cannot be grouped, so it is skipped — the rule is about functions
    sharing a parameter type, which requires the type to be visible).
    """
    if not node.args.args:
        return None
    first = node.args.args[0]
    if first.annotation is None:
        return None
    return ast.unparse(first.annotation)


def _module_functions(path: Path) -> list[tuple[str, int, str]]:
    """(function_name, lineno, first_param_annotation) for module-level
    functions (and async functions) — methods are not module-level, so
    classes are never scanned."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    found: list[tuple[str, int, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotation = _first_param_annotation(node)
            if annotation is not None:
                found.append((node.name, node.lineno, annotation))
    return found


def scan(paths: list[Path], threshold: int) -> tuple[list[str], list[str]]:
    """Returns (findings, warnings) as formatted lines.

    Findings: groups of >= threshold free functions sharing a leading
    parameter — the missed class. Warnings: groups of threshold-1 (the
    prompt to consolidate before it becomes a finding).
    """
    files = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
        elif p.is_file() and p.suffix == ".py":
            files.append(p)
    by_file: dict[Path, list[tuple[str, int, str]]] = {}
    for f in files:
        functions = _module_functions(f)
        if functions:
            by_file[f] = functions
    findings: list[str] = []
    warnings: list[str] = []
    for f, functions in sorted(by_file.items()):
        groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for name, lineno, annotation in functions:
            groups[annotation].append((name, lineno))
        for annotation, members in sorted(groups.items()):
            if len(members) >= threshold:
                names = ", ".join(f"{n} (line {ln})" for n, ln in sorted(members, key=lambda m: m[1]))
                annotation_txt = f"'{annotation}'"
                findings.append(
                    f"{f}: {len(members)} free functions share leading parameter "
                    + f"{annotation_txt} — a {annotation} class is missing: {names}"
                )
            elif threshold > 2 and len(members) == threshold - 1:
                names = ", ".join(f"{n} (line {ln})" for n, ln in sorted(members, key=lambda m: m[1]))
                annotation_txt = f"'{annotation}'"
                warnings.append(
                    f"{f}: {len(members)} free functions share leading parameter "
                    + f"{annotation_txt} — consolidate before it becomes a finding: {names}"
                )
    return findings, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_missed_classes",
        description="Detect function strewing: free functions sharing a leading parameter are a missed class.",
    )
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories to scan (.py)")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help=f"finding threshold (default {DEFAULT_THRESHOLD}); threshold-1 groups warn")
    args = parser.parse_args(argv)
    findings, warnings = scan([Path(p) for p in args.paths], args.threshold)
    for w in warnings:
        print(f"  warn: {w}")
    if findings:
        print("missed classes found (free functions sharing a leading parameter):")
        for f in findings:
            print(f"  {f}")
        return 1
    print(f"ok — no missed classes in {len(args.paths)} path(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
