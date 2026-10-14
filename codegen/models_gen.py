"""schema/schema.yaml → app/generated/db/models.py."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from codegen.render import CodegenError, env, header, ruff_format, sha256, write

SOURCE = "schema/schema.yaml"
OUTPUT = "app/generated/db/models.py"
SPEC_SCHEMA = Path(__file__).with_name("schema_spec.json")

SA_TYPES = {
    "integer": "Integer()",
    "bigint": "BigInteger()",
    "string": "String({length})",
    "text": "Text()",
    "boolean": "Boolean()",
    "datetime": "DateTime(timezone=True)",
}
PY_TYPES = {
    "integer": "int",
    "bigint": "int",
    "string": "str",
    "text": "str",
    "boolean": "bool",
    "datetime": "datetime",
}
SERVER_DEFAULTS = {"now": "func.now()", "true": "true()", "false": "false()"}


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate(data)
    return data


def validate(data: dict) -> None:
    try:
        jsonschema.validate(data, json.loads(SPEC_SCHEMA.read_text(encoding="utf-8")))
    except jsonschema.ValidationError as e:
        where = "/".join(map(str, e.absolute_path))
        raise CodegenError(f"schema.yaml が不正です: {e.message} (at {where})") from e
    tables = data["tables"]
    for tname, t in tables.items():
        is_assoc = t.get("association", False)
        if is_assoc == ("model" in t):
            raise CodegenError(
                f"{tname}: 通常テーブルは model 必須、association テーブルは model 不可"
            )
        if is_assoc and t.get("relationships"):
            raise CodegenError(f"{tname}: association テーブルに relationships は書けません")
        if not any(c.get("primary_key") for c in t["columns"].values()):
            raise CodegenError(f"{tname}: primary_key がありません")
        for cname, c in t["columns"].items():
            if c["type"] == "string" and "length" not in c:
                raise CodegenError(f"{tname}.{cname}: string には length が必要です")
            if fk := c.get("foreign_key"):
                ft, _, fc = fk.partition(".")
                if ft not in tables or fc not in tables[ft]["columns"]:
                    raise CodegenError(f"{tname}.{cname}: foreign_key {fk} の参照先がありません")
        for rname, r in t.get("relationships", {}).items():
            target = tables.get(r["target"])
            if target is None or "model" not in target:
                raise CodegenError(
                    f"{tname}.{rname}: target {r['target']} はモデルテーブルではありません"
                )
            sec = r.get("secondary")
            if sec is not None and not tables.get(sec, {}).get("association"):
                raise CodegenError(
                    f"{tname}.{rname}: secondary {sec} は association テーブルではありません"
                )
            bp = r.get("back_populates")
            if bp is not None and bp not in target.get("relationships", {}):
                raise CodegenError(
                    f"{tname}.{rname}: back_populates {bp} が {r['target']} にありません"
                )


def _column_args(name: str, c: dict, *, with_name: bool) -> str:
    args = [repr(name)] if with_name else []
    args.append(SA_TYPES[c["type"]].format(length=c.get("length")))
    if fk := c.get("foreign_key"):
        ondelete = f", ondelete={c['on_delete']!r}" if "on_delete" in c else ""
        args.append(f"ForeignKey({fk!r}{ondelete})")
    if c.get("primary_key"):
        args.append("primary_key=True")
    else:
        args.append(f"nullable={bool(c.get('nullable', False))}")
    if c.get("unique"):
        args.append("unique=True")
    if c.get("index"):
        args.append("index=True")
    if sd := c.get("server_default"):
        args.append(f"server_default={SERVER_DEFAULTS[sd]}")
    if cm := c.get("comment"):
        args.append(f"comment={cm!r}")
    return ", ".join(args)


def _annotation(c: dict) -> str:
    t = PY_TYPES[c["type"]]
    return f"{t} | None" if c.get("nullable") and not c.get("primary_key") else t


def render(data: dict, digest: str) -> str:
    validate(data)
    tables = data["tables"]
    class_of = {n: t["model"] for n, t in tables.items() if "model" in t}
    associations, models = [], []
    for name, t in tables.items():
        if t.get("association"):
            associations.append(
                {
                    "name": name,
                    "comment": t.get("comment"),
                    "columns": [
                        _column_args(cn, c, with_name=True) for cn, c in t["columns"].items()
                    ],
                }
            )
            continue
        rels = []
        for rname, r in t.get("relationships", {}).items():
            target = class_of[r["target"]]
            args = [repr(target)]
            if sec := r.get("secondary"):
                args.append(f"secondary={sec!r}")
            if bp := r.get("back_populates"):
                args.append(f"back_populates={bp!r}")
            rels.append(
                {
                    "name": rname,
                    "annotation": f"list[{target}]" if r.get("many") else target,
                    "args": ", ".join(args),
                }
            )
        models.append(
            {
                "class_name": t["model"],
                "table": name,
                "comment": t.get("comment"),
                "columns": [
                    {
                        "name": cn,
                        "annotation": _annotation(c),
                        "args": _column_args(cn, c, with_name=False),
                    }
                    for cn, c in t["columns"].items()
                ],
                "relationships": rels,
            }
        )
    return (
        env()
        .get_template("models.py.j2")
        .render(
            header=header(SOURCE, digest, "make generate"),
            associations=associations,
            models=models,
        )
    )


def write_package_inits(root: Path) -> list[Path]:
    paths = []
    for rel in (
        "app/generated/__init__.py",
        "app/generated/db/__init__.py",
        "app/generated/api/__init__.py",
    ):
        p = root / rel
        write(p, header("codegen", "-" * 16, "make generate"))
        paths.append(p)
    return paths


def generate(root: Path) -> list[Path]:
    src = root / SOURCE
    out = root / OUTPUT
    write(out, render(load(src), sha256(src)))
    paths = [out, *write_package_inits(root)]
    ruff_format(paths)
    return paths
