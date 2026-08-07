"""Record-shaped collection check — "never a bare dict as a record".

The rule from docs/coding-standards.md: structured data is an object with
named fields, not a bare dict, tuple, or nested list. This tool gates on
the two places records appear:

1. **Signatures** — record-shaped collections in parameters and returns:
   grab-bags (`dict[str, Any]`, bare `dict`), collections of dicts or
   tuples (`list[dict[str, str]]`, `list[tuple[A, B]]`), nested lists, and
   fixed tuples. Maps pass: `dict[str, T]` (including primitive-valued
   maps like counts) is a lookup, not a record; `list[T]` of a domain
   class is a collection. Deserializer boundaries are the one sanctioned
   bare-dict spot: a grab-bag parameter on a function that returns a
   domain class (raw JSON in, `Label` out) is exempt.
2. **Literals** — a dict literal with >= 2 constant string keys and at
   least one dynamic value, in a *record position* (assigned, returned, or
   yielded), is a record being built (`{"kind": "tool_call", ...}`).
   Inline call arguments (`headers={...}`) are maps, not records, and pass.
   Lookup tables whose keys and values are all constant pass untouched.

Function strewing (free functions sharing a leading parameter) is a
canary for the same disease; it is reported as a warning, never the gate.

Stdlib-only (this is a config repo — no deps).

    python3 tools/check_missed_classes.py [paths...]
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import defaultdict
from pathlib import Path

# Primitive value types: a dict of these (in a signature) is a record, not a map.
PRIMITIVES = frozenset({"str", "int", "float", "bool", "bytes", "Any", "object", "None"})


class ScanResult:
    """Findings fail the gate; warnings are the strewing canary."""

    findings: list[str]
    warnings: list[str]

    def __init__(self, findings: list[str], warnings: list[str]) -> None:
        self.findings = findings
        self.warnings = warnings


class ModuleScanner:
    """All checks over one parsed module."""

    tree: ast.Module
    path: Path

    def __init__(self, tree: ast.Module, path: Path) -> None:
        self.tree = tree
        self.path = path

    @staticmethod
    def _name_of(node: ast.expr | None) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return str(node.value)
        return None

    @classmethod
    def _is_grab_bag(cls, node: ast.expr) -> bool:
        """A bare dict or one whose value type says nothing about its shape
        (dict[str, Any], dict[Any, X], dict[str, object]) — an untyped record."""
        if isinstance(node, ast.Name):
            return node.id == "dict"
        if not isinstance(node, ast.Subscript):
            return False
        base = node.value
        if not isinstance(base, ast.Name) or base.id != "dict":
            return False
        value = node.slice
        if isinstance(value, ast.Tuple):
            _, val = value.elts
            return cls._name_of(val) in ("Any", "object", "None")
        return True  # dict[X] single-arg

    @classmethod
    def _annotation_is_record(cls, node: ast.expr | None) -> bool:
        """True when an annotation is a record-shaped bare collection.

        Calibration: maps pass (dict[str, primitive], dict[str, Domain]);
        grab-bags fail (bare dict, dict[str, Any]); collections of dicts /
        tuples / nested lists fail; fixed tuples fail.
        """
        if node is None:
            return False
        if isinstance(node, ast.Name):
            return node.id in ("dict", "tuple")
        if not isinstance(node, ast.Subscript):
            return False
        base = node.value
        if not isinstance(base, ast.Name):
            return False
        if base.id == "dict":
            value = node.slice
            if isinstance(value, ast.Tuple):
                key, val = value.elts
                if cls._name_of(key) not in ("str", "Any"):
                    return False
                val_name = cls._name_of(val)
                if val_name in ("Any", "object", "None"):
                    return True  # grab-bag: no shape
                if isinstance(val, ast.Subscript):
                    return True  # values are themselves collections (records)
                if isinstance(val, ast.Name) and val.id in ("dict", "tuple", "list"):
                    return True
                return False  # dict[str, primitive | domain] = a map
            return True  # dict[X] single-arg or dict[()] — bare-ish
        if base.id == "tuple":
            return True  # a fixed-size pair is a record
        if base.id == "list":
            value = node.slice
            if isinstance(value, ast.Subscript):
                return True  # list[dict[...]] / list[tuple[...]] / list[list[...]] — records
            return isinstance(value, ast.Name) and value.id in ("dict", "tuple", "list")
        return False

    @staticmethod
    def _returns_domain_class(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Return annotation is a single class name (Label, Run, ...) — the
        function converts raw JSON into a domain object."""
        r = node.returns
        if r is None:
            return False
        if isinstance(r, ast.Name):
            return r.id not in PRIMITIVES and r.id not in ("dict", "tuple", "list")
        return False

    def signature_findings(self) -> list[str]:
        findings: list[str] = []
        for node in ast.walk(self.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            boundary = self._returns_domain_class(node)
            args = node.args.args + node.args.posonlyargs + node.args.kwonlyargs
            for arg in args:
                ann_node = arg.annotation
                if ann_node is None or not self._annotation_is_record(ann_node):
                    continue
                if boundary and self._is_grab_bag(ann_node):
                    continue  # deserializer boundary: raw JSON in, domain class out
                ann = ast.unparse(ann_node)
                findings.append(
                    f"{self.path}: bare record collection '{ann}' in parameter "
                    + f"'{arg.arg}' of {node.name} (line {node.lineno})"
                )
            returns_node = node.returns
            if returns_node is not None and self._annotation_is_record(returns_node):
                ann = ast.unparse(returns_node)
                findings.append(
                    f"{self.path}: bare record collection '{ann}' as return type "
                    + f"of {node.name} (line {node.lineno})"
                )
        return findings

    def record_literal_lines(self) -> list[int]:
        """Line numbers of dict literals building records: >= 2 keys, >= 1
        constant string key, >= 1 dynamic value, in a record position
        (assigned, returned, or yielded). Inline call arguments are maps
        and are not descended into. Lookup tables (all values constant)
        pass."""
        found: set[int] = set()

        def scan_expr(node: ast.expr | None) -> None:
            if node is None:
                return
            if isinstance(node, ast.Dict):
                keys = node.keys
                has_const_key = any(
                    isinstance(k, ast.Constant) and isinstance(k.value, str) for k in keys
                )
                has_dynamic_value = any(not isinstance(v, ast.Constant) for v in node.values)
                if len(keys) >= 2 and has_const_key and has_dynamic_value:
                    found.add(node.lineno)
                for v in node.values:
                    scan_expr(v)
                return
            if isinstance(node, (ast.List, ast.Tuple)):
                for elt in node.elts:
                    scan_expr(elt)
            elif isinstance(node, ast.IfExp):
                scan_expr(node.body)
                scan_expr(node.orelse)
            # Do NOT descend into Call nodes: inline arguments (headers={...},
            # params={...}) are maps/config, not records.

        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Return, ast.Yield, ast.YieldFrom)):
                scan_expr(getattr(node, "value", None))
        return sorted(found)

    def strewing_warnings(self) -> list[str]:
        """Free module-level functions sharing a leading parameter — the canary."""
        functions: list[tuple[str, int, str]] = []
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.args.args:
                    continue
                annotation = node.args.args[0].annotation
                if annotation is None:
                    continue
                functions.append((node.name, node.lineno, ast.unparse(annotation)))
        groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for name, lineno, annotation in functions:
            groups[annotation].append((name, lineno))
        warnings: list[str] = []
        for annotation, members in sorted(groups.items()):
            if len(members) >= 2:
                names = ", ".join(f"{n} (line {ln})" for n, ln in sorted(members, key=lambda m: m[1]))
                warnings.append(
                    f"{self.path}: {len(members)} free functions share leading parameter "
                    + f"'{annotation}' — a {annotation} class is missing: {names}"
                )
        return warnings


def scan(paths: list[Path]) -> ScanResult:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
        elif p.is_file() and p.suffix == ".py":
            files.append(p)
    findings: list[str] = []
    warnings: list[str] = []
    for f in files:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        scanner = ModuleScanner(tree, f)
        findings.extend(scanner.signature_findings())
        findings.extend(
            f"{f}: dict literal with constant keys is a record — make a class (line {ln})"
            for ln in scanner.record_literal_lines()
        )
        warnings.extend(scanner.strewing_warnings())
    return ScanResult(findings, warnings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_missed_classes",
        description="Gate on record-shaped collections (bare dict/tuple/nested list); warn on function strewing.",
    )
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories to scan (.py)")
    args = parser.parse_args(argv)
    result = scan([Path(p) for p in args.paths])
    for w in result.warnings:
        print(f"  warn: {w}")
    if result.findings:
        print("record-shaped collections found (make a class):")
        for f in result.findings:
            print(f"  {f}")
        return 1
    print(f"ok — no record-shaped collections in {len(args.paths)} path(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
