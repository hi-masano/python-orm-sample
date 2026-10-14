"""SQLAlchemy MetaData → docs/er/schema.md (Mermaid erDiagram)."""

from __future__ import annotations

import importlib
from pathlib import Path

from sqlalchemy import Column, MetaData
from sqlalchemy.dialects import postgresql

from codegen.render import write

OUTPUT = "docs/er/schema.md"
MODELS_MODULE = "app.generated.db.models"


def _type(col: Column) -> str:
    return col.type.compile(dialect=postgresql.dialect()).replace(" ", "_")


def render(metadata: MetaData) -> str:
    lines = ["erDiagram"]
    tables = sorted(metadata.tables.values(), key=lambda t: t.name)
    for table in tables:
        lines.append(f"    {table.name} {{")
        for col in table.columns:
            flags = (
                ("PK", col.primary_key),
                ("FK", bool(col.foreign_keys)),
                ("UK", bool(col.unique)),
            )
            keys = [k for k, on in flags if on]
            key = f" {','.join(keys)}" if keys else ""
            null = "nullable" if col.nullable else "not null"
            lines.append(f'        {_type(col)} {col.name}{key} "{null}"')
        lines.append("    }")
    for table in tables:
        for fk in sorted(table.foreign_keys, key=lambda f: f.parent.name):
            card = "|o--o{" if fk.parent.nullable else "||--o{"
            lines.append(f'    {fk.column.table.name} {card} {table.name} : "{fk.parent.name}"')
    return "\n".join(lines) + "\n"


def generate(root: Path) -> list[Path]:
    module = importlib.reload(importlib.import_module(MODELS_MODULE))
    body = render(module.Base.metadata)
    text = (
        "<!-- このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT). -->\n"
        "<!-- source: app/generated/db/models.py / regenerate: make generate -->\n\n"
        "# ER 図\n\n```mermaid\n" + body + "```\n"
    )
    out = root / OUTPUT
    write(out, text)
    return [out]
