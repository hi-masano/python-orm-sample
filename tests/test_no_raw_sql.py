"""app/impl と seeds で生 SQL を使っていないことを AST で検査する (ruff banned-api の補完)."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TARGETS = sorted([*ROOT.glob("app/impl/**/*.py"), *ROOT.glob("seeds/**/*.py")])
FORBIDDEN_CALLS = {"text", "exec_driver_sql", "literal_column"}


def _violations(tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in FORBIDDEN_CALLS:
                found.append(f"line {node.lineno}: {name}()")
            if (
                name == "execute"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.append(f"line {node.lineno}: execute('<SQL文字列>')")
    return found


def test_detector_catches_raw_sql():
    assert _violations(ast.parse("s.execute('SELECT 1')\nconn.exec_driver_sql('x')\ntext('y')"))


@pytest.mark.parametrize("path", TARGETS, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_raw_sql(path):
    assert _violations(ast.parse(path.read_text("utf-8"))) == []
