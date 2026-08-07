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

DICT_STR_SIGNATURE = """\
def render(config: dict[str, str]) -> str:
    return config["name"]
"""

MAP_COUNTS = """\
def counts() -> dict[str, int]:
    return {}
"""

DICT_ANY_RETURN = """\
def build() -> dict[str, Any]:
    return {}
"""

TUPLE_SIGNATURE = """\
def classify(item: str) -> tuple[int, bool]:
    return 1, True
"""

NESTED_LIST_SIGNATURE = """\
def parse_all(raw: list[dict[str, Any]]) -> None:
    pass
"""

LIST_OF_PRIMITIVE_DICT = """\
def executions() -> list[dict[str, str]]:
    return []
"""

DICT_OF_COLLECTION = """\
def start_by_call() -> dict[str, dict[str, str]]:
    return {}
"""

MAP_OF_DOMAIN_OK = """\
def index(labels: dict[str, Label]) -> None:
    pass
"""

LIST_OF_DOMAIN_OK = """\
def collect(runs: list[Run]) -> None:
    return runs
"""

LIST_OF_STR_OK = """\
def names(items: list[str]) -> list[str]:
    return items
"""

DESERIALIZER_BOUNDARY = """\
def from_line(line: dict[str, Any]) -> Label:
    return Label(line["call_id"])
"""

WRAPPED_DESERIALIZER = """\
def from_line(line: dict[str, Any]) -> Label | None:
    return None
"""

OPTIONAL_DESERIALIZER = """\
def from_line(line: dict[str, Any]) -> Optional[Label]:
    return None
"""

UNION_VALUE_MAP = """\
def merge(opts: dict[str, str | None]) -> None:
    pass
"""

GRAB_BAG_TO_PRIMITIVE = """\
def created_ms(line: dict[str, Any]) -> int:
    return int(line["created_at_ms"])
"""

RECORD_LITERAL = """\
def make_item(block):
    return {"kind": "tool_call", "call_id": block.get("id")}
"""

LOOKUP_TABLE_OK = """\
PHASE_UI = {"prd": "PRD", "exec": "Execute", "ux": "UX loop"}
"""

MIXED_RECORD_LITERAL = """\
def tag(kind, value):
    return {"kind": kind, "value": value, "extra": 1}
"""

HEADERS_MAP = """\
def _get_json(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    return json.load(urllib.request.urlopen(req))
"""

ASSIGNED_RECORD = """\
def make_item(block):
    item = {"kind": "tool_call", "call_id": block.get("id")}
    return item
"""

INLINE_ARG_RECORD = """\
def render(block):
    return format_({"kind": "tool_call", "call_id": block.get("id")})
"""


class RecordCollectionGateTest(unittest.TestCase):
    def test_dict_str_signature_is_a_map_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", DICT_STR_SIGNATURE)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_primitive_map_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", MAP_COUNTS)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_dict_any_return_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", DICT_ANY_RETURN)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_tuple_signature_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", TUPLE_SIGNATURE)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)
            self.assertIn("tuple[int, bool]", result.findings[0])

    def test_nested_list_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", NESTED_LIST_SIGNATURE)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_list_of_primitive_dict_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", LIST_OF_PRIMITIVE_DICT)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_dict_of_collection_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", DICT_OF_COLLECTION)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_map_of_domain_class_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", MAP_OF_DOMAIN_OK)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_list_of_domain_class_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", LIST_OF_DOMAIN_OK)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_list_of_primitive_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", LIST_OF_STR_OK)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_deserializer_boundary_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", DESERIALIZER_BOUNDARY)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_wrapped_deserializer_return_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", WRAPPED_DESERIALIZER)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_optional_deserializer_return_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", OPTIONAL_DESERIALIZER)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_union_value_map_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", UNION_VALUE_MAP)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_grab_bag_to_primitive_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", GRAB_BAG_TO_PRIMITIVE)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_record_dict_literal_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", RECORD_LITERAL)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)
            self.assertIn("record", result.findings[0])

    def test_lookup_table_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", LOOKUP_TABLE_OK)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_mixed_record_literal_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", MIXED_RECORD_LITERAL)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_headers_map_literal_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", HEADERS_MAP)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])

    def test_assigned_record_literal_is_a_finding(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", ASSIGNED_RECORD)
            result = scan([Path(td)])
            self.assertEqual(len(result.findings), 1)

    def test_inline_arg_record_literal_is_exempt(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", INLINE_ARG_RECORD)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])


class StrewingWarningTest(unittest.TestCase):
    def test_three_shared_params_warns_not_fails(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", THREE_SHARED)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])  # strewing is a warning, not the gate
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("3 free functions", result.warnings[0])

    def test_two_shared_params_warns(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", TWO_SHARED)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])
            self.assertEqual(len(result.warnings), 1)
            self.assertIn("2 free functions", result.warnings[0])

    def test_different_leading_params_is_clean(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", DIFFERENT_LEADS)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])
            self.assertEqual(result.warnings, [])

    def test_class_methods_are_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", METHODS_ONLY)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])
            self.assertEqual(result.warnings, [])

    def test_unannotated_first_params_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "m.py", UNANNOTATED)
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])
            self.assertEqual(result.warnings, [])

    def test_directory_walk_and_single_file(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "a.py", THREE_SHARED)
            write_module(Path(td), "b.py", DIFFERENT_LEADS)
            self.assertEqual(len(scan([Path(td)]).warnings), 1)
            self.assertEqual(len(scan([Path(td) / "a.py"]).warnings), 1)
            self.assertEqual(scan([Path(td) / "b.py"]).warnings, [])

    def test_broken_source_is_skipped_not_crashed(self):
        with tempfile.TemporaryDirectory() as td:
            write_module(Path(td), "broken.py", "def f(:")
            result = scan([Path(td)])
            self.assertEqual(result.findings, [])
            self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
