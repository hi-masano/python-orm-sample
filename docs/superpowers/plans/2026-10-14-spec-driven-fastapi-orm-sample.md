# 仕様駆動 FastAPI + PostgreSQL + SQLAlchemy サンプル Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 宣言的スキーマ YAML と OpenAPI を唯一の正とし、ORM モデル・マイグレーション・ER 図・API のガワ・テスト用型を**機械的に**生成する FastAPI/PostgreSQL サンプルを作り、AI は実装スロット (`app/impl/`) と仕様ファイルだけを触れるガードレールを敷く。

**Architecture:**
`schema/schema.yaml` → 自作ジェネレータ → `app/generated/db/models.py` (SQLAlchemy 2.0) → `alembic revision --autogenerate` → `migrations/versions/*` (post_write_hook で ER 図・チェックサム更新)。`openapi/openapi.yaml` → datamodel-code-generator (Pydantic DTO) + 自作ジェネレータ (FastAPI ルータ + 抽象ハンドラ ABC) → `app/generated/api/*`、openapi-typescript → `e2e/generated/api.d.ts`。AI は `app/impl/handlers.py` で ABC を実装し、ORM 経由で DB アクセスする。生成物の改ざんは「再生成して git diff」で検出 (pre-commit / CI)、加えて Claude Code PreToolUse フックで書き込みを allowlist 制限。

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy 2.0 / Alembic / psycopg3 / Pydantic v2 / datamodel-code-generator / Jinja2 / jsonschema / ruff / pytest / uv (コンテナ内) / PostgreSQL 17 / Docker Compose / Playwright Test (TypeScript) / openapi-typescript

**Spec:** ユーザー要求 (本プランの Context 節に要約)。リポジトリは `README.md` のみの空状態 (branch `feature/generate-sample`)。

## Context

ユーザー要求の要点と決定事項:
- PostgreSQL + FastAPI。ORM は SQLAlchemy、スキーマ定義を管理。
- マイグレーションは Alembic。※Flask-Migrate は Flask 専用の Alembic ラッパーなので、FastAPI では **Alembic を直接使う** (中身は同じ)。
- ER 図は AI 推論ではなく仕組みで自動出力 → モデルの `MetaData` から Mermaid を機械生成。`make generate` と Alembic の `post_write_hooks` の両方に連携。
- API は ORM モデル経由のみ (生 SQL 禁止 → ruff banned-api + AST テストで強制)。
- Playwright (TypeScript, `request` fixture) で、compose で立てたコンテナの `http://localhost:8000` へ実アクセス。データは ORM ベースの seeder で投入 (Playwright globalSetup から呼ぶ)。
- OpenAPI 定義から API ソースを自動生成。
- **決定 (ユーザー回答)**: SoT は宣言的スキーマ YAML / OpenAPI YAML。**AI は仕様ファイルの編集は可**、生成物・ジェネレータ・配線は編集不可。Playwright は TypeScript。ドメインは users / posts / tags。

## Global Constraints

- Python `>=3.12,<3.13` (コンテナ `python:3.12-slim`)。ホストには uv も Python 3.12 も前提にしない — Python 系コマンドは全て `docker compose run tools ...` 経由。
- Node はホスト (v24 確認済み) で `e2e/` のみに使用。
- PostgreSQL `postgres:17-alpine`、接続 `postgresql+psycopg://app:app@db:5432/app` (ローカル専用のテスト値)。
- JSON フィールド・パス/クエリパラメータ名は **snake_case**、OpenAPI component 名は **PascalCase**、operationId は camelCase (→ 関数名は snake_case に変換)。
- 生成物には必ず先頭に `# このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT).` 行と source の sha256 を入れる。
- 生成物ディレクトリ: `app/generated/`, `docs/er/`, `e2e/generated/`, `migrations/versions/` (最後のみチェックサム方式)。
- AI 書き込み可 (allowlist): `schema/`, `openapi/`, `app/impl/`, `seeds/`, `tests/impl/`, `e2e/tests/`, `docs/` (ただし `docs/er/` 除く), `README.md`。
- ガードレールのフック (Task 10) は**最後に**有効化する (先に入れると本プランを実装する AI 自身がブロックされるため)。有効化後のジェネレータ変更は人間のみ。

## File Structure

```
schema/schema.yaml               DB スキーマの正 (AI 編集可)
openapi/openapi.yaml             API 仕様の正 (AI 編集可)
codegen/                         ジェネレータ (人間のみ)
  __init__.py  __main__.py       CLI: models | er | api | all | checksum-record | checksum-verify
  render.py                      CodegenError, Jinja env, header, ruff_format, sha256
  schema_spec.json               schema.yaml の JSON Schema
  models_gen.py  er_gen.py  api_gen.py  checksums.py
  templates/models.py.j2  routers.py.j2  handlers.py.j2
app/
  generated/{__init__,db/__init__,db/models,api/__init__,api/schemas,api/handlers,api/routers}.py  (DO NOT EDIT)
  core/config.py  core/db.py     設定・Session (人間のみ)
  main.py                        配線 (人間のみ)
  impl/__init__.py  impl/handlers.py   ★AI が書く中身
migrations/env.py  script.py.mako  versions/  checksums.txt
alembic.ini
seeds/__init__.py  run.py  e2e.py    ORM ベース seeder (AI 編集可)
docs/er/schema.md                ER 図 (生成物)
tests/codegen/*  tests/test_contract.py  tests/test_guard_hook.py  tests/test_no_raw_sql.py  tests/impl/
e2e/package.json  playwright.config.ts  global-setup.ts  tsconfig.json  tests/*.spec.ts  generated/api.d.ts
.claude/settings.json  .claude/hooks/guard.py   CLAUDE.md
Dockerfile  docker-compose.yml  .dockerignore  .gitignore  Makefile  pyproject.toml  uv.lock
.githooks/pre-commit  .github/workflows/ci.yml
```

---

### Task 0: プランをリポジトリに保存

- [ ] **Step 1:** 本ファイルを `docs/superpowers/plans/2026-10-14-spec-driven-fastapi-orm-sample.md` にコピー。
- [ ] **Step 2:** `git add docs/superpowers/plans && git commit -m "docs: add implementation plan"`

---

### Task 1: Python プロジェクト骨格とコンテナ実行環境

**Files:** Create `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.gitignore`, `Makefile`, `uv.lock`(生成), `tests/test_smoke.py`

**Interfaces:** Produces: `make build`, `make test`, `make lint`, `make lock`; compose サービス `db`, `tools`(profile tools, `.:/workspace` マウント, venv は `/opt/venv`)。

- [ ] **Step 1: `pyproject.toml`**

```toml
[project]
name = "python-orm-sample"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.30",
  "sqlalchemy>=2.0.30,<2.1",
  "alembic>=1.13,<2",
  "psycopg[binary]>=3.2,<4",
  "pydantic>=2.7,<3",
  "pydantic-settings>=2.3,<3",
  "email-validator>=2.1",
  "pyyaml>=6",
]

[dependency-groups]
dev = [
  "datamodel-code-generator>=0.26,<1",
  "jinja2>=3.1",
  "jsonschema>=4.22",
  "ruff>=0.6",
  "pytest>=8",
  "httpx>=0.27",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "TID"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"sqlalchemy.text".msg = "生SQL禁止: ORM モデル経由でアクセスすること"
"sqlalchemy.sql.text".msg = "生SQL禁止: ORM モデル経由でアクセスすること"
"sqlalchemy.sql.expression.text".msg = "生SQL禁止: ORM モデル経由でアクセスすること"
"psycopg".msg = "DB ドライバの直接利用禁止: ORM モデル経由でアクセスすること"

[tool.ruff.lint.per-file-ignores]
"app/generated/**" = ["E501", "F401", "I"]
"migrations/**" = ["E501", "F401", "I", "TID251"]
```

- [ ] **Step 2: `Dockerfile`**

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 3: `docker-compose.yml`** (api サービスは Task 6 で追加)

```yaml
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 2s
      timeout: 3s
      retries: 30
  tools:
    build: .
    profiles: ["tools"]
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@db:5432/app
    volumes: [".:/workspace"]
    depends_on:
      db: { condition: service_healthy }
volumes:
  pgdata: {}
```

- [ ] **Step 4: `.dockerignore` / `.gitignore`**

`.dockerignore`: `.git`, `e2e/node_modules`, `e2e/playwright-report`, `e2e/test-results`, `**/__pycache__`, `.pytest_cache`, `.ruff_cache`
`.gitignore`: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `e2e/node_modules/`, `e2e/playwright-report/`, `e2e/test-results/`

- [ ] **Step 5: `Makefile`** (以降のタスクで target を追記)

```make
COMPOSE  := docker compose
TOOLS    := $(COMPOSE) run --rm --no-deps tools
TOOLS_DB := $(COMPOSE) run --rm tools

.PHONY: lock build test lint
lock:
	docker run --rm -v "$(CURDIR)":/w -w /w ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim uv lock
build:
	$(COMPOSE) --profile tools build
test:
	$(TOOLS) pytest -q
lint:
	$(TOOLS) ruff check .
	$(TOOLS) ruff format --check .
```

- [ ] **Step 6: スモークテスト `tests/test_smoke.py`**

```python
import sqlalchemy


def test_sqlalchemy_is_2x():
    assert sqlalchemy.__version__.startswith("2.")
```

- [ ] **Step 7:** `make lock && make build && make test` → `1 passed`
- [ ] **Step 8: Commit** `git add -A && git commit -m "chore: python project skeleton with containerized tooling"`

---

### Task 2: スキーマ YAML → SQLAlchemy モデル生成

**Files:** Create `codegen/__init__.py`(空), `codegen/render.py`, `codegen/schema_spec.json`, `codegen/models_gen.py`, `codegen/templates/models.py.j2`, `codegen/__main__.py`, `schema/schema.yaml`, `tests/codegen/__init__.py`, `tests/codegen/test_models_gen.py`; 生成 `app/__init__.py`(空・手書き), `app/generated/**`

**Interfaces:**
- Produces: `codegen.render.CodegenError`, `render.env() -> jinja2.Environment` (filter `pyrepr`), `render.header(source: str, digest: str, command: str) -> str`, `render.sha256(path: Path) -> str`, `render.write(path: Path, text: str) -> None`, `render.ruff_format(paths: list[Path]) -> None`
- Produces: `models_gen.load(path: Path) -> dict`, `models_gen.validate(data: dict) -> None`, `models_gen.render(data: dict, digest: str) -> str`, `models_gen.generate(root: Path) -> list[Path]` (全ジェネレータの公開入口は `generate(root)` に統一)
- Produces: 生成モジュール `app.generated.db.models` に `Base`, `User`, `Post`, `Tag`, `post_tags`
- CLI: `python -m codegen models|all`

- [ ] **Step 1: 失敗するテスト `tests/codegen/test_models_gen.py`**

```python
import copy

import pytest

from codegen import models_gen
from codegen.render import CodegenError

VALID = {
    "tables": {
        "users": {
            "model": "User",
            "comment": "利用者",
            "columns": {
                "id": {"type": "integer", "primary_key": True},
                "email": {"type": "string", "length": 255, "unique": True},
                "created_at": {"type": "datetime", "server_default": "now"},
            },
            "relationships": {"posts": {"target": "posts", "many": True, "back_populates": "author"}},
        },
        "posts": {
            "model": "Post",
            "columns": {
                "id": {"type": "integer", "primary_key": True},
                "author_id": {"type": "integer", "foreign_key": "users.id", "on_delete": "CASCADE"},
                "note": {"type": "text", "nullable": True},
            },
            "relationships": {"author": {"target": "users", "back_populates": "posts"}},
        },
    }
}


def _mutated(fn):
    data = copy.deepcopy(VALID)
    fn(data)
    return data


def test_valid_schema_passes():
    models_gen.validate(VALID)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["tables"]["users"]["columns"]["email"].pop("length"), "length"),
        (lambda d: d["tables"]["posts"]["columns"]["author_id"].update(foreign_key="nope.id"), "参照先"),
        (lambda d: d["tables"]["posts"]["relationships"]["author"].update(target="ghosts"), "target"),
        (lambda d: d["tables"]["posts"]["relationships"]["author"].update(back_populates="x"), "back_populates"),
        (lambda d: d["tables"]["users"]["columns"]["id"].update(type="uuid"), "不正"),
        (lambda d: d["tables"]["users"].pop("model"), "model"),
    ],
)
def test_invalid_schema_raises(mutate, message):
    with pytest.raises(CodegenError, match=message):
        models_gen.validate(_mutated(mutate))


def test_render_is_deterministic_and_executable():
    first = models_gen.render(VALID, "abc")
    assert first == models_gen.render(VALID, "abc")
    assert first.startswith("# このファイルは自動生成されています")
    namespace: dict = {}
    exec(compile(first, "models.py", "exec"), namespace)
    users = namespace["Base"].metadata.tables["users"]
    posts = namespace["Base"].metadata.tables["posts"]
    assert users.c.email.unique is True
    assert users.c.email.type.length == 255
    assert posts.c.note.nullable is True
    assert posts.c.author_id.nullable is False
    fk = next(iter(posts.c.author_id.foreign_keys))
    assert fk.target_fullname == "users.id" and fk.ondelete == "CASCADE"
    assert users.comment == "利用者"
```

- [ ] **Step 2:** `make test` → FAIL (`ModuleNotFoundError: codegen`)

- [ ] **Step 3: `codegen/render.py`**

```python
"""ジェネレータ共通ユーティリティ."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import jinja2

TEMPLATES = Path(__file__).with_name("templates")


class CodegenError(Exception):
    """仕様ファイルがジェネレータの対応範囲外/不正なときに送出する."""


def env() -> jinja2.Environment:
    e = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATES),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=jinja2.StrictUndefined,
    )
    e.filters["pyrepr"] = repr
    return e


def header(source: str, digest: str, command: str) -> str:
    return (
        "# このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT).\n"
        f"# source: {source} (sha256: {digest[:16]})\n"
        f"# regenerate: {command}\n"
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ruff_format(paths: list[Path]) -> None:
    subprocess.run(["ruff", "format", "--quiet", *map(str, paths)], check=True)
```

- [ ] **Step 4: `codegen/schema_spec.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["tables"],
  "additionalProperties": false,
  "properties": {
    "tables": {
      "type": "object",
      "minProperties": 1,
      "propertyNames": {"pattern": "^[a-z][a-z0-9_]*$"},
      "additionalProperties": {
        "type": "object",
        "required": ["columns"],
        "additionalProperties": false,
        "properties": {
          "model": {"type": "string", "pattern": "^[A-Z][A-Za-z0-9]*$"},
          "association": {"type": "boolean"},
          "comment": {"type": "string"},
          "columns": {
            "type": "object",
            "minProperties": 1,
            "propertyNames": {"pattern": "^[a-z][a-z0-9_]*$"},
            "additionalProperties": {
              "type": "object",
              "required": ["type"],
              "additionalProperties": false,
              "properties": {
                "type": {"enum": ["integer", "bigint", "string", "text", "boolean", "datetime"]},
                "length": {"type": "integer", "minimum": 1},
                "primary_key": {"type": "boolean"},
                "nullable": {"type": "boolean"},
                "unique": {"type": "boolean"},
                "index": {"type": "boolean"},
                "foreign_key": {"type": "string", "pattern": "^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$"},
                "on_delete": {"enum": ["CASCADE", "SET NULL", "RESTRICT"]},
                "server_default": {"enum": ["now", "true", "false"]},
                "comment": {"type": "string"}
              }
            }
          },
          "relationships": {
            "type": "object",
            "propertyNames": {"pattern": "^[a-z][a-z0-9_]*$"},
            "additionalProperties": {
              "type": "object",
              "required": ["target"],
              "additionalProperties": false,
              "properties": {
                "target": {"type": "string"},
                "many": {"type": "boolean"},
                "secondary": {"type": "string"},
                "back_populates": {"type": "string"}
              }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 5: `codegen/models_gen.py`**

```python
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
            raise CodegenError(f"{tname}: 通常テーブルは model 必須、association テーブルは model 不可")
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
                raise CodegenError(f"{tname}.{rname}: target {r['target']} はモデルテーブルではありません")
            sec = r.get("secondary")
            if sec is not None and not tables.get(sec, {}).get("association"):
                raise CodegenError(f"{tname}.{rname}: secondary {sec} は association テーブルではありません")
            bp = r.get("back_populates")
            if bp is not None and bp not in target.get("relationships", {}):
                raise CodegenError(f"{tname}.{rname}: back_populates {bp} が {r['target']} にありません")


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
            associations.append({
                "name": name,
                "comment": t.get("comment"),
                "columns": [_column_args(cn, c, with_name=True) for cn, c in t["columns"].items()],
            })
            continue
        rels = []
        for rname, r in t.get("relationships", {}).items():
            target = class_of[r["target"]]
            args = [repr(target)]
            if sec := r.get("secondary"):
                args.append(f"secondary={sec!r}")
            if bp := r.get("back_populates"):
                args.append(f"back_populates={bp!r}")
            rels.append({
                "name": rname,
                "annotation": f"list[{target}]" if r.get("many") else target,
                "args": ", ".join(args),
            })
        models.append({
            "class_name": t["model"],
            "table": name,
            "comment": t.get("comment"),
            "columns": [
                {"name": cn, "annotation": _annotation(c), "args": _column_args(cn, c, with_name=False)}
                for cn, c in t["columns"].items()
            ],
            "relationships": rels,
        })
    return env().get_template("models.py.j2").render(
        header=header(SOURCE, digest, "make generate"),
        associations=associations,
        models=models,
    )


def write_package_inits(root: Path) -> list[Path]:
    paths = []
    for rel in ("app/generated/__init__.py", "app/generated/db/__init__.py", "app/generated/api/__init__.py"):
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
```

- [ ] **Step 6: `codegen/templates/models.py.j2`**

```jinja
{{ header }}
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    false,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

{% for t in associations %}

{{ t.name }} = Table(
    {{ t.name|pyrepr }},
    Base.metadata,
{% for col in t.columns %}
    Column({{ col }}),
{% endfor %}
{% if t.comment %}
    comment={{ t.comment|pyrepr }},
{% endif %}
)
{% endfor %}
{% for m in models %}


class {{ m.class_name }}(Base):
    __tablename__ = {{ m.table|pyrepr }}
{% if m.comment %}
    __table_args__ = {"comment": {{ m.comment|pyrepr }}}
{% endif %}

{% for c in m.columns %}
    {{ c.name }}: Mapped[{{ c.annotation }}] = mapped_column({{ c.args }})
{% endfor %}
{% for r in m.relationships %}
    {{ r.name }}: Mapped[{{ r.annotation }}] = relationship({{ r.args }})
{% endfor %}
{% endfor %}
```

- [ ] **Step 7: `codegen/__main__.py`** (後続タスクで分岐を追記)

```python
"""python -m codegen <command>  — 全生成物の唯一の生成入口."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from codegen import models_gen
from codegen.render import CodegenError

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codegen")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("models", "all"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    try:
        if args.cmd in ("models", "all"):
            models_gen.generate(ROOT)
    except CodegenError as e:
        print(f"codegen error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8: `schema/schema.yaml`**

```yaml
# DB スキーマの唯一の正 (Source of Truth)。
# 編集後: make generate → make migration m="変更内容"
tables:
  users:
    model: User
    comment: 利用者
    columns:
      id: {type: integer, primary_key: true}
      email: {type: string, length: 255, unique: true, comment: ログイン用メールアドレス}
      name: {type: string, length: 100}
      created_at: {type: datetime, server_default: now}
    relationships:
      posts: {target: posts, many: true, back_populates: author}
  posts:
    model: Post
    comment: 投稿
    columns:
      id: {type: integer, primary_key: true}
      author_id: {type: integer, foreign_key: users.id, on_delete: CASCADE, index: true}
      title: {type: string, length: 200}
      body: {type: text}
      published: {type: boolean, server_default: "false"}
      created_at: {type: datetime, server_default: now}
    relationships:
      author: {target: users, back_populates: posts}
      tags: {target: tags, many: true, secondary: post_tags, back_populates: posts}
  tags:
    model: Tag
    comment: タグ
    columns:
      id: {type: integer, primary_key: true}
      name: {type: string, length: 50, unique: true}
    relationships:
      posts: {target: posts, many: true, secondary: post_tags, back_populates: tags}
  post_tags:
    association: true
    comment: posts と tags の中間テーブル
    columns:
      post_id: {type: integer, primary_key: true, foreign_key: posts.id, on_delete: CASCADE}
      tag_id: {type: integer, primary_key: true, foreign_key: tags.id, on_delete: CASCADE}
```

- [ ] **Step 9:** Makefile に追記:

```make
.PHONY: generate
generate:
	$(TOOLS) python -m codegen all
```

`app/__init__.py` を空で作成。`make build && make generate && make test` → PASS。`app/generated/db/models.py` を目視 (User/Post/Tag と `post_tags = Table(...)`)。`make generate` を 2 回実行して `git status` に差分が出ないこと (決定性) を確認。
- [ ] **Step 10: Commit** `git add -A && git commit -m "feat(codegen): generate SQLAlchemy models from schema.yaml"`

---

### Task 3: ER 図 (Mermaid) 自動生成

**Files:** Create `codegen/er_gen.py`, `tests/codegen/test_er_gen.py`; Modify `codegen/__main__.py`; 生成 `docs/er/schema.md`

**Interfaces:** Consumes `app.generated.db.models.Base`. Produces `er_gen.render(metadata: MetaData) -> str`, `er_gen.generate(root: Path) -> list[Path]`; CLI `python -m codegen er`。

- [ ] **Step 1: 失敗するテスト**

```python
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

from codegen import er_gen


def test_render_mermaid():
    md = MetaData()
    Table("users", md, Column("id", Integer, primary_key=True), Column("email", String(255), unique=True))
    Table(
        "posts", md,
        Column("id", Integer, primary_key=True),
        Column("author_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("editor_id", Integer, ForeignKey("users.id"), nullable=True),
    )
    out = er_gen.render(md)
    assert out.startswith("erDiagram\n")
    assert "    users {\n        INTEGER id PK \"not null\"\n        VARCHAR(255) email UK" in out
    assert '    users ||--o{ posts : "author_id"' in out
    assert '    users |o--o{ posts : "editor_id"' in out
    assert out == er_gen.render(md)
```

- [ ] **Step 2:** `make test` → FAIL
- [ ] **Step 3: `codegen/er_gen.py`**

```python
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
            keys = [k for k, on in (("PK", col.primary_key), ("FK", bool(col.foreign_keys)), ("UK", bool(col.unique))) if on]
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
```

- [ ] **Step 4:** `codegen/__main__.py` に `er` サブコマンド追加: `for name in ("models", "er", "all")`、`from codegen import er_gen, models_gen`、`if args.cmd in ("er", "all"): er_gen.generate(ROOT)` (models の後)。
- [ ] **Step 5:** `make generate && make test` → PASS。`docs/er/schema.md` に users/posts/tags/post_tags と 4 本のリレーション線があること。
- [ ] **Step 6: Commit** `git add -A && git commit -m "feat(codegen): generate mermaid ER diagram from ORM metadata"`

---

### Task 4: Alembic 設定 + マイグレーションチェックサム + 初期マイグレーション

**Files:** Create `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/.gitkeep`, `codegen/checksums.py`, `tests/codegen/test_checksums.py`, `app/core/__init__.py`, `app/core/config.py`; Modify `codegen/__main__.py`, `Makefile`; 生成 `migrations/versions/*_initial_schema.py`, `migrations/checksums.txt`

**Interfaces:** Produces `app.core.config.settings.database_url: str`; `checksums.record(root: Path, file: Path) -> None`, `checksums.verify(root: Path) -> list[str]` (エラー文字列リスト); CLI `checksum-record <path>`, `checksum-verify`; make `migration m=...`, `migrate`, `check-migrations`。

- [ ] **Step 1: 失敗するテスト `tests/codegen/test_checksums.py`**

```python
from codegen import checksums


def test_record_and_verify(tmp_path):
    versions = tmp_path / "migrations" / "versions"
    versions.mkdir(parents=True)
    f = versions / "001_init.py"
    f.write_text("x = 1\n")
    checksums.record(tmp_path, f)
    assert checksums.verify(tmp_path) == []
    f.write_text("x = 2\n")
    assert any("001_init.py" in e for e in checksums.verify(tmp_path))
    (versions / "002_new.py").write_text("y = 1\n")
    assert any("002_new.py" in e and "未登録" in e for e in checksums.verify(tmp_path))
```

- [ ] **Step 2:** `make test` → FAIL
- [ ] **Step 3: `codegen/checksums.py`**

```python
"""migrations/versions の改ざん検知用マニフェスト (migrations/checksums.txt)."""

from __future__ import annotations

from pathlib import Path

from codegen.render import sha256

MANIFEST = "migrations/checksums.txt"
VERSIONS = "migrations/versions"


def _load(root: Path) -> dict[str, str]:
    path = root / MANIFEST
    if not path.exists():
        return {}
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        entries[name] = digest
    return entries


def record(root: Path, file: Path) -> None:
    entries = _load(root)
    entries[file.resolve().name] = sha256(file)
    lines = [f"{d}  {n}" for n, d in sorted(entries.items())]
    (root / MANIFEST).write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify(root: Path) -> list[str]:
    entries = _load(root)
    errors = []
    files = {p.name: p for p in (root / VERSIONS).glob("*.py")}
    for name, path in sorted(files.items()):
        if name not in entries:
            errors.append(f"{name}: チェックサム未登録 (alembic revision 以外で作成された可能性)")
        elif entries[name] != sha256(path):
            errors.append(f"{name}: 生成後に改変されています")
    for name in sorted(set(entries) - set(files)):
        errors.append(f"{name}: マニフェストにあるがファイルがありません")
    return errors
```

- [ ] **Step 4:** `codegen/__main__.py` に追加:

```python
    rec = sub.add_parser("checksum-record")
    rec.add_argument("path")
    sub.add_parser("checksum-verify")
    ...
        if args.cmd == "checksum-record":
            checksums.record(ROOT, Path(args.path))
        if args.cmd == "checksum-verify":
            errors = checksums.verify(ROOT)
            for e in errors:
                print(f"migration checksum error: {e}", file=sys.stderr)
            return 1 if errors else 0
```

- [ ] **Step 5: `app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"


settings = Settings()
```

- [ ] **Step 6: `alembic.ini`**

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

[post_write_hooks]
# 生成直後に: 整形 → チェックサム登録 → ER 図再生成 (順序が重要)
hooks = ruff_format, checksum, er_diagram
ruff_format.type = exec
ruff_format.executable = ruff
ruff_format.options = format REVISION_SCRIPT_FILENAME
checksum.type = exec
checksum.executable = python
checksum.options = -m codegen checksum-record REVISION_SCRIPT_FILENAME
er_diagram.type = exec
er_diagram.executable = python
er_diagram.options = -m codegen er

[loggers]
keys = root,sqlalchemy,alembic
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARNING
handlers = console
qualname =
[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine
[logger_alembic]
level = INFO
handlers =
qualname = alembic
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 7: `migrations/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.generated.db.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 8: `migrations/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

このファイルは alembic revision --autogenerate で自動生成されています。直接編集しないでください (DO NOT EDIT).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 9:** Makefile に追記:

```make
.PHONY: migration migrate check-migrations
migration:
	@test -n "$(m)" || (echo 'usage: make migration m="message"' && exit 1)
	$(TOOLS_DB) sh -c 'alembic upgrade head && alembic revision --autogenerate -m "$(m)"'
migrate:
	$(TOOLS_DB) alembic upgrade head
check-migrations:
	$(TOOLS) python -m codegen checksum-verify
	$(TOOLS_DB) sh -c 'alembic upgrade head && alembic check'
```

- [ ] **Step 10:** `make build && make test` → PASS。`make migration m="initial schema"` → `migrations/versions/*_initial_schema.py` (create_table ×4) と `migrations/checksums.txt` が生成されること。`make check-migrations` → `No new upgrade operations detected.` で成功。改ざんテスト: マイグレーションに空行を足し `make check-migrations` が失敗 → `git checkout` で戻す。
- [ ] **Step 11: Commit** `git add -A && git commit -m "feat(db): alembic with checksum-guarded autogenerated migrations"`

---

### Task 5: OpenAPI → Pydantic DTO + FastAPI ルータ + 抽象ハンドラ生成

**Files:** Create `openapi/openapi.yaml`, `codegen/api_gen.py`, `codegen/templates/routers.py.j2`, `codegen/templates/handlers.py.j2`, `tests/codegen/test_api_gen.py`; Modify `codegen/__main__.py`; 生成 `app/generated/api/{schemas,handlers,routers}.py`

**Interfaces:**
- Produces: `api_gen.parse_operations(spec: dict) -> list[Operation]`, `api_gen.generate(root: Path) -> list[Path]`
- Produces (生成コード): `app.generated.api.schemas` (`Health, User, UserCreate, Tag, Post, PostCreate, Error`), `app.generated.api.handlers.ApiHandlers` (ABC。メソッドは keyword-only 引数), `app.generated.api.routers.build_router(get_handlers: Callable[..., ApiHandlers]) -> APIRouter`
- ハンドラメソッド (operationId → snake_case): `health_check() -> Health`, `list_users(*, limit: int, offset: int) -> list[User]`, `create_user(*, body: UserCreate) -> User`, `get_user(*, user_id: int) -> User`, `list_posts(*, tag: str | None, author_id: int | None) -> list[Post]`, `create_post(*, body: PostCreate) -> Post`, `get_post(*, post_id: int) -> Post`, `delete_post(*, post_id: int) -> None`, `list_tags() -> list[Tag]`

- [ ] **Step 1: 失敗するテスト `tests/codegen/test_api_gen.py`**

```python
import pytest

from codegen import api_gen
from codegen.render import CodegenError

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "t", "version": "1"},
    "paths": {
        "/items/{item_id}": {
            "get": {
                "operationId": "getItem",
                "parameters": [
                    {"name": "item_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20, "minimum": 1}},
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": {200: {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}}}},
            },
            "delete": {
                "operationId": "deleteItem",
                "parameters": [{"name": "item_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"204": {"description": "deleted"}},
            },
        },
        "/items": {
            "post": {
                "operationId": "createItem",
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ItemCreate"}}}},
                "responses": {"201": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Item"}}}}},
            }
        },
    },
}


def test_parse_operations():
    ops = {o.operation_id: o for o in api_gen.parse_operations(SPEC)}
    get = ops["getItem"]
    assert (get.func_name, get.method, get.status_code, get.response_type) == ("get_item", "get", 200, "schemas.Item")
    assert get.signature == [
        "item_id: Annotated[int, Path()]",
        "handlers: Annotated[ApiHandlers, Depends(get_handlers)]",
        "limit: Annotated[int, Query(ge=1)] = 20",
        "q: Annotated[str | None, Query()] = None",
    ]
    assert get.call_args == "item_id=item_id, limit=limit, q=q"
    assert ops["deleteItem"].status_code == 204 and ops["deleteItem"].response_type is None
    create = ops["createItem"]
    assert create.status_code == 201 and create.signature[0] == "body: Annotated[schemas.ItemCreate, Body()]"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda s: s["paths"]["/items"]["post"].pop("operationId"), "operationId"),
        (lambda s: s["paths"]["/items/{item_id}"]["delete"]["parameters"].clear(), "item_id"),
        (lambda s: s["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"].update({"$ref": "#/components/schemas/bad_name"}), "PascalCase"),
        (lambda s: s["paths"]["/items/{item_id}"]["get"]["parameters"][2].update(name="qQ"), "snake_case"),
        (lambda s: s["paths"]["/items"]["post"].update(responses={"400": {}}), "2xx"),
    ],
)
def test_parse_errors(mutate, message):
    import copy

    spec = copy.deepcopy(SPEC)
    mutate(spec)
    with pytest.raises(CodegenError, match=message):
        api_gen.parse_operations(spec)
```

- [ ] **Step 2:** `make test` → FAIL
- [ ] **Step 3: `codegen/api_gen.py`**

```python
"""openapi/openapi.yaml → app/generated/api/{schemas,handlers,routers}.py.

DTO は datamodel-code-generator、ルータと抽象ハンドラは本モジュールが生成する。
対応範囲外の OpenAPI 構文は CodegenError で即失敗させる (黙って無視しない)。
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from codegen.render import CodegenError, env, header, ruff_format, sha256, write

SOURCE = "openapi/openapi.yaml"
OUT_DIR = "app/generated/api"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")
PRIMITIVES = {"integer": "int", "number": "float", "string": "str", "boolean": "bool"}
CONSTRAINTS = {"minimum": "ge", "maximum": "le", "minLength": "min_length", "maxLength": "max_length"}
REF_PREFIX = "#/components/schemas/"


@dataclass(frozen=True)
class Param:
    name: str
    location: str
    py_type: str
    required: bool
    default: Any
    constraints: tuple[tuple[str, Any], ...]

    def signature(self) -> str:
        fn = "Path" if self.location == "path" else "Query"
        cargs = ", ".join(f"{k}={v!r}" for k, v in self.constraints)
        if self.required:
            return f"{self.name}: Annotated[{self.py_type}, {fn}({cargs})]"
        if self.default is None:
            return f"{self.name}: Annotated[{self.py_type} | None, {fn}({cargs})] = None"
        return f"{self.name}: Annotated[{self.py_type}, {fn}({cargs})] = {self.default!r}"

    def handler_param(self) -> str:
        optional = not self.required and self.default is None
        return f"{self.name}: {self.py_type}{' | None' if optional else ''}"


@dataclass(frozen=True)
class Operation:
    operation_id: str
    func_name: str
    method: str
    path: str
    status_code: int
    response_type: str | None
    body_type: str | None
    params: tuple[Param, ...]
    tags: tuple[str, ...]
    summary: str | None

    @property
    def signature(self) -> list[str]:
        parts = [f"body: Annotated[{self.body_type}, Body()]"] if self.body_type else []
        parts += [p.signature() for p in self.params if p.required]
        parts.append("handlers: Annotated[ApiHandlers, Depends(get_handlers)]")
        parts += [p.signature() for p in self.params if not p.required]
        return parts

    @property
    def call_args(self) -> str:
        names = (["body"] if self.body_type else []) + [p.name for p in self.params]
        return ", ".join(f"{n}={n}" for n in names)

    @property
    def handler_params(self) -> list[str]:
        head = [f"body: {self.body_type}"] if self.body_type else []
        return head + [p.handler_param() for p in self.params]


def to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def schema_type(schema: dict, where: str) -> str:
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith(REF_PREFIX):
            raise CodegenError(f"{where}: 未対応の $ref {ref}")
        name = ref[len(REF_PREFIX):]
        if not PASCAL.match(name):
            raise CodegenError(f"{where}: component 名 {name} は PascalCase にしてください")
        return f"schemas.{name}"
    t = schema.get("type")
    if t == "array":
        return f"list[{schema_type(schema['items'], where)}]"
    if t in PRIMITIVES:
        return PRIMITIVES[t]
    raise CodegenError(f"{where}: 未対応のスキーマ {schema}")


def _param(raw: dict, where: str) -> Param:
    if "$ref" in raw:
        raise CodegenError(f"{where}: parameters の $ref は未対応です")
    name, loc = raw["name"], raw.get("in")
    if loc not in ("path", "query"):
        raise CodegenError(f"{where}: パラメータ {name} の in={loc} は未対応です")
    if not SNAKE.match(name):
        raise CodegenError(f"{where}: パラメータ名 {name} は snake_case にしてください")
    schema = raw.get("schema", {})
    py_type = schema_type(schema, where)
    if py_type not in PRIMITIVES.values():
        raise CodegenError(f"{where}: パラメータ {name} はプリミティブ型のみ対応です")
    constraints = tuple((CONSTRAINTS[k], schema[k]) for k in CONSTRAINTS if k in schema)
    required = loc == "path" or bool(raw.get("required", False))
    return Param(name, loc, py_type, required, schema.get("default"), constraints)


def _success(responses: dict, where: str) -> tuple[int, str | None]:
    normalized = {str(k): v for k, v in responses.items()}
    codes = sorted(int(c) for c in normalized if c.startswith("2"))
    if not codes:
        raise CodegenError(f"{where}: 2xx レスポンスが定義されていません")
    code = codes[0]
    content = (normalized[str(code)] or {}).get("content")
    if code == 204 or not content:
        return code, None
    if "application/json" not in content:
        raise CodegenError(f"{where}: レスポンスは application/json のみ対応です")
    return code, schema_type(content["application/json"]["schema"], where)


def parse_operations(spec: dict) -> list[Operation]:
    ops: list[Operation] = []
    for path, item in spec.get("paths", {}).items():
        for method in HTTP_METHODS:
            op = item.get(method)
            if op is None:
                continue
            where = f"{method.upper()} {path}"
            op_id = op.get("operationId")
            if not op_id:
                raise CodegenError(f"{where}: operationId が必要です")
            params = tuple(_param(p, where) for p in [*item.get("parameters", []), *op.get("parameters", [])])
            declared = {p.name for p in params if p.location == "path"}
            for name in re.findall(r"{([^}]+)}", path):
                if name not in declared:
                    raise CodegenError(f"{where}: パスパラメータ {name} が parameters にありません")
            body_type = None
            if "requestBody" in op:
                content = op["requestBody"].get("content", {})
                if "application/json" not in content:
                    raise CodegenError(f"{where}: requestBody は application/json のみ対応です")
                body_type = schema_type(content["application/json"]["schema"], where)
            status, response_type = _success(op.get("responses", {}), where)
            ops.append(Operation(
                operation_id=op_id, func_name=to_snake(op_id), method=method, path=path,
                status_code=status, response_type=response_type, body_type=body_type,
                params=params, tags=tuple(op.get("tags", [])), summary=op.get("summary"),
            ))
    ids = [o.operation_id for o in ops]
    if dupes := {i for i in ids if ids.count(i) > 1}:
        raise CodegenError(f"operationId が重複しています: {sorted(dupes)}")
    return ops


def generate(root: Path) -> list[Path]:
    src = root / SOURCE
    digest = sha256(src)
    ops = parse_operations(yaml.safe_load(src.read_text(encoding="utf-8")))
    out = root / OUT_DIR
    hdr = header(SOURCE, digest, "make generate")
    schemas_py = out / "schemas.py"
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "datamodel-codegen",
            "--input", str(src),
            "--input-file-type", "openapi",
            "--output", str(schemas_py),
            "--output-model-type", "pydantic_v2.BaseModel",
            "--target-python-version", "3.12",
            "--use-standard-collections",
            "--use-union-operator",
            "--field-constraints",
            "--disable-timestamp",
            "--custom-file-header", hdr.rstrip("\n"),
        ],
        check=True,
    )
    e = env()
    handlers_py, routers_py = out / "handlers.py", out / "routers.py"
    write(handlers_py, e.get_template("handlers.py.j2").render(header=hdr, operations=ops))
    write(routers_py, e.get_template("routers.py.j2").render(header=hdr, operations=ops))
    paths = [schemas_py, handlers_py, routers_py]
    ruff_format(paths)
    return paths
```

- [ ] **Step 4: `codegen/templates/handlers.py.j2`**

```jinja
{{ header }}
from __future__ import annotations

from abc import ABC, abstractmethod

from app.generated.api import schemas


class ApiHandlers(ABC):
    """OpenAPI の各 operation に 1:1 対応する実装インターフェース.

    実装は app/impl/handlers.py の Handlers クラスで行う。
    """
{% for op in operations %}

    @abstractmethod
    def {{ op.func_name }}(self{% if op.handler_params %}, *, {{ op.handler_params|join(", ") }}{% endif %}) -> {{ op.response_type or "None" }}:
        """{{ op.method|upper }} {{ op.path }}{% if op.summary %} — {{ op.summary }}{% endif %}"""
{% endfor %}
```

- [ ] **Step 5: `codegen/templates/routers.py.j2`**

```jinja
{{ header }}
from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Response

from app.generated.api import schemas
from app.generated.api.handlers import ApiHandlers


def build_router(get_handlers: Callable[..., ApiHandlers]) -> APIRouter:
    router = APIRouter()
{% for op in operations %}

    @router.{{ op.method }}(
        {{ op.path|pyrepr }},
        operation_id={{ op.operation_id|pyrepr }},
        status_code={{ op.status_code }},
        response_model={{ op.response_type or "None" }},
        tags={{ op.tags|list|pyrepr }},
        summary={{ op.summary|pyrepr }},
    )
    def {{ op.func_name }}(
{% for p in op.signature %}
        {{ p }},
{% endfor %}
    ) -> {{ op.response_type or "Response" }}:
{% if op.response_type %}
        return handlers.{{ op.func_name }}({{ op.call_args }})
{% else %}
        handlers.{{ op.func_name }}({{ op.call_args }})
        return Response(status_code={{ op.status_code }})
{% endif %}
{% endfor %}

    return router
```

> 注意: routers.py には `from __future__ import annotations` を**入れない**。`get_handlers` はクロージャ変数なので、注釈が文字列化されると FastAPI が `Depends(get_handlers)` を解決できなくなる。

- [ ] **Step 6: `openapi/openapi.yaml`**

```yaml
openapi: 3.0.3
info:
  title: python-orm-sample API
  version: 0.1.0
  description: API 仕様の唯一の正 (Source of Truth)。編集後は make generate。
paths:
  /health:
    get:
      operationId: healthCheck
      tags: [system]
      summary: ヘルスチェック
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {$ref: "#/components/schemas/Health"}}}
  /users:
    get:
      operationId: listUsers
      tags: [users]
      summary: ユーザー一覧
      parameters:
        - {name: limit, in: query, schema: {type: integer, minimum: 1, maximum: 100, default: 20}}
        - {name: offset, in: query, schema: {type: integer, minimum: 0, default: 0}}
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {type: array, items: {$ref: "#/components/schemas/User"}}}}
    post:
      operationId: createUser
      tags: [users]
      summary: ユーザー作成
      requestBody:
        required: true
        content: {application/json: {schema: {$ref: "#/components/schemas/UserCreate"}}}
      responses:
        "201":
          description: Created
          content: {application/json: {schema: {$ref: "#/components/schemas/User"}}}
        "409":
          description: email が重複
          content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}
  /users/{user_id}:
    get:
      operationId: getUser
      tags: [users]
      summary: ユーザー取得
      parameters:
        - {name: user_id, in: path, required: true, schema: {type: integer}}
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {$ref: "#/components/schemas/User"}}}
        "404":
          description: Not Found
          content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}
  /posts:
    get:
      operationId: listPosts
      tags: [posts]
      summary: 投稿一覧
      parameters:
        - {name: tag, in: query, schema: {type: string}}
        - {name: author_id, in: query, schema: {type: integer}}
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {type: array, items: {$ref: "#/components/schemas/Post"}}}}
    post:
      operationId: createPost
      tags: [posts]
      summary: 投稿作成
      requestBody:
        required: true
        content: {application/json: {schema: {$ref: "#/components/schemas/PostCreate"}}}
      responses:
        "201":
          description: Created
          content: {application/json: {schema: {$ref: "#/components/schemas/Post"}}}
        "400":
          description: author が存在しない
          content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}
  /posts/{post_id}:
    get:
      operationId: getPost
      tags: [posts]
      summary: 投稿取得
      parameters:
        - {name: post_id, in: path, required: true, schema: {type: integer}}
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {$ref: "#/components/schemas/Post"}}}
        "404":
          description: Not Found
          content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}
    delete:
      operationId: deletePost
      tags: [posts]
      summary: 投稿削除
      parameters:
        - {name: post_id, in: path, required: true, schema: {type: integer}}
      responses:
        "204": {description: Deleted}
        "404":
          description: Not Found
          content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}
  /tags:
    get:
      operationId: listTags
      tags: [tags]
      summary: タグ一覧
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {type: array, items: {$ref: "#/components/schemas/Tag"}}}}
components:
  schemas:
    Health:
      type: object
      required: [status]
      properties: {status: {type: string}}
    Error:
      type: object
      required: [detail]
      properties: {detail: {type: string}}
    User:
      type: object
      required: [id, email, name, created_at]
      properties:
        id: {type: integer}
        email: {type: string, format: email}
        name: {type: string}
        created_at: {type: string, format: date-time}
    UserCreate:
      type: object
      required: [email, name]
      properties:
        email: {type: string, format: email, maxLength: 255}
        name: {type: string, minLength: 1, maxLength: 100}
    Tag:
      type: object
      required: [id, name]
      properties:
        id: {type: integer}
        name: {type: string}
    Post:
      type: object
      required: [id, author_id, title, body, published, tags, created_at]
      properties:
        id: {type: integer}
        author_id: {type: integer}
        title: {type: string}
        body: {type: string}
        published: {type: boolean}
        tags: {type: array, items: {$ref: "#/components/schemas/Tag"}}
        created_at: {type: string, format: date-time}
    PostCreate:
      type: object
      required: [author_id, title, body]
      properties:
        author_id: {type: integer}
        title: {type: string, minLength: 1, maxLength: 200}
        body: {type: string}
        published: {type: boolean, default: false}
        tag_names:
          type: array
          default: []
          items: {type: string, minLength: 1, maxLength: 50}
```

- [ ] **Step 7:** `codegen/__main__.py` に `api` を追加 (`for name in ("models", "er", "api", "all")`, `if args.cmd in ("api", "all"): api_gen.generate(ROOT)`)。
- [ ] **Step 8:** `make generate && make test && make lint` → PASS。生成された `routers.py` に 9 ルート、`handlers.py` に 9 abstractmethod があること。`schemas.py` の datamodel-codegen 出力で `--custom-file-header` が効いていること (先頭が DO NOT EDIT)。もし datamodel-codegen のバージョンで `--custom-file-header` が無い場合は `uv.lock` 上のバージョンを `datamodel-codegen --help | grep custom-file-header` で確認し、フラグが存在するバージョンに pin する。
- [ ] **Step 9: Commit** `git add -A && git commit -m "feat(codegen): generate FastAPI routers and handler ABC from OpenAPI"`

---

### Task 6: アプリ配線 + 契約テスト + api コンテナ

**Files:** Create `app/core/db.py`, `app/main.py`, `app/impl/__init__.py`, `app/impl/handlers.py` (この時点では全メソッド `raise NotImplementedError` のスタブ), `tests/test_contract.py`; Modify `docker-compose.yml`, `Makefile`

**Interfaces:** Produces `app.core.db.SessionLocal`, `app.core.db.get_session() -> Iterator[Session]`, `app.main.app: FastAPI`, `app.main.create_app() -> FastAPI`; `app.impl.handlers.Handlers(session: Session)` (ApiHandlers 実装)。

- [ ] **Step 1: 失敗するテスト `tests/test_contract.py`**

```python
from pathlib import Path

import yaml
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.impl.handlers import Handlers
from app.main import app

SPEC = yaml.safe_load((Path(__file__).resolve().parent.parent / "openapi/openapi.yaml").read_text("utf-8"))
METHODS = {"get", "post", "put", "patch", "delete"}


def test_routes_match_spec():
    expected = {
        (m.upper(), path, op["operationId"])
        for path, item in SPEC["paths"].items()
        for m, op in item.items()
        if m in METHODS
    }
    actual = {
        (m, r.path, r.operation_id)
        for r in app.routes
        if isinstance(r, APIRoute)
        for m in r.methods
    }
    assert actual == expected


def test_impl_implements_every_operation():
    assert not Handlers.__abstractmethods__


def test_served_openapi_is_the_spec_file():
    assert TestClient(app).get("/openapi.json").json() == SPEC
```

- [ ] **Step 2:** `make test` → FAIL (`app.main` なし)
- [ ] **Step 3: `app/core/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
```

- [ ] **Step 4: `app/main.py`**

```python
"""配線のみ。生成ルータに実装 (app/impl) を注入する。"""

from pathlib import Path
from typing import Annotated

import yaml
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.generated.api.routers import build_router
from app.impl.handlers import Handlers

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi" / "openapi.yaml"


def get_handlers(session: Annotated[Session, Depends(get_session)]) -> Handlers:
    return Handlers(session)


def create_app() -> FastAPI:
    if missing := sorted(Handlers.__abstractmethods__):
        raise RuntimeError(f"app/impl/handlers.py に未実装の operation があります: {missing}")
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    app = FastAPI(title=spec["info"]["title"], version=spec["info"]["version"])
    app.include_router(build_router(get_handlers))
    app.openapi = lambda: spec  # 公開する OpenAPI は仕様ファイルそのもの
    return app


app = create_app()
```

- [ ] **Step 5: `app/impl/handlers.py` スタブ** — `class Handlers(ApiHandlers)` に `__init__(self, session: Session)` と、Task 5 Interfaces に列挙した 9 メソッドを同シグネチャで定義し本体は `raise NotImplementedError`。(Task 7 で実装)
- [ ] **Step 6: `docker-compose.yml` に api を追加**

```yaml
  api:
    build: .
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@db:5432/app
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 2s
      timeout: 3s
      retries: 30
```

Makefile: `up: ; $(COMPOSE) up -d --build --wait db api` / `down: ; $(COMPOSE) down -v --remove-orphans` (.PHONY に追加)。
- [ ] **Step 7:** `make build && make test` → PASS (contract 3 件)
- [ ] **Step 8: Commit** `git add -A && git commit -m "feat(app): wire generated router to impl handlers with contract tests"`

---

### Task 7: ハンドラ実装 (ORM のみ) + 生 SQL 禁止ガード

**Files:** Modify `app/impl/handlers.py`; Create `tests/test_no_raw_sql.py`, `tests/impl/__init__.py`

**Interfaces:** Consumes `app.generated.db.models.{User,Post,Tag}`, `app.generated.api.schemas.*`, `ApiHandlers`。

- [ ] **Step 1: 失敗するテスト `tests/test_no_raw_sql.py`**

```python
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
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in FORBIDDEN_CALLS:
                found.append(f"line {node.lineno}: {name}()")
            if name == "execute" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                found.append(f"line {node.lineno}: execute('<SQL文字列>')")
    return found


def test_detector_catches_raw_sql():
    assert _violations(ast.parse("s.execute('SELECT 1')\nconn.exec_driver_sql('x')\ntext('y')"))


@pytest.mark.parametrize("path", TARGETS, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_raw_sql(path):
    assert _violations(ast.parse(path.read_text("utf-8"))) == []
```

- [ ] **Step 2:** `make up` 後に `curl -s localhost:8000/health` → 500 (NotImplementedError) を確認 (実装前の失敗確認)。
- [ ] **Step 3: `app/impl/handlers.py` 実装**

```python
"""OpenAPI operation の実装。DB アクセスは ORM モデル経由のみ (生 SQL 禁止)。"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.generated.api import schemas
from app.generated.api.handlers import ApiHandlers
from app.generated.db import models


class Handlers(ApiHandlers):
    def __init__(self, session: Session) -> None:
        self.session = session

    def health_check(self) -> schemas.Health:
        return schemas.Health(status="ok")

    def list_users(self, *, limit: int, offset: int) -> list[schemas.User]:
        stmt = select(models.User).order_by(models.User.id).limit(limit).offset(offset)
        return [schemas.User.model_validate(u, from_attributes=True) for u in self.session.scalars(stmt)]

    def create_user(self, *, body: schemas.UserCreate) -> schemas.User:
        exists = self.session.scalar(select(models.User).where(models.User.email == body.email))
        if exists is not None:
            raise HTTPException(status_code=409, detail="email already exists")
        user = models.User(email=body.email, name=body.name)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return schemas.User.model_validate(user, from_attributes=True)

    def get_user(self, *, user_id: int) -> schemas.User:
        user = self.session.get(models.User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        return schemas.User.model_validate(user, from_attributes=True)

    def list_posts(self, *, tag: str | None, author_id: int | None) -> list[schemas.Post]:
        stmt = select(models.Post).options(selectinload(models.Post.tags)).order_by(models.Post.id)
        if tag is not None:
            stmt = stmt.where(models.Post.tags.any(models.Tag.name == tag))
        if author_id is not None:
            stmt = stmt.where(models.Post.author_id == author_id)
        return [schemas.Post.model_validate(p, from_attributes=True) for p in self.session.scalars(stmt)]

    def create_post(self, *, body: schemas.PostCreate) -> schemas.Post:
        if self.session.get(models.User, body.author_id) is None:
            raise HTTPException(status_code=400, detail="author not found")
        tags = [self._get_or_create_tag(name) for name in dict.fromkeys(body.tag_names)]
        post = models.Post(
            author_id=body.author_id, title=body.title, body=body.body, published=body.published, tags=tags
        )
        self.session.add(post)
        self.session.commit()
        self.session.refresh(post)
        return schemas.Post.model_validate(post, from_attributes=True)

    def get_post(self, *, post_id: int) -> schemas.Post:
        return schemas.Post.model_validate(self._post_or_404(post_id), from_attributes=True)

    def delete_post(self, *, post_id: int) -> None:
        self.session.delete(self._post_or_404(post_id))
        self.session.commit()

    def list_tags(self) -> list[schemas.Tag]:
        stmt = select(models.Tag).order_by(models.Tag.name)
        return [schemas.Tag.model_validate(t, from_attributes=True) for t in self.session.scalars(stmt)]

    def _post_or_404(self, post_id: int) -> models.Post:
        post = self.session.get(models.Post, post_id, options=[selectinload(models.Post.tags)])
        if post is None:
            raise HTTPException(status_code=404, detail="post not found")
        return post

    def _get_or_create_tag(self, name: str) -> models.Tag:
        tag = self.session.scalar(select(models.Tag).where(models.Tag.name == name))
        return tag if tag is not None else models.Tag(name=name)
```

> `schemas.PostCreate.tag_names` は datamodel-codegen 出力で `list[str] | None = []` 等になる可能性がある。生成物の実際の型を確認し、`None` 許容なら `body.tag_names or []` とすること。

- [ ] **Step 4:** `make up` → `curl -s localhost:8000/health` → `{"status":"ok"}`、`curl -s -XPOST localhost:8000/users -H 'content-type: application/json' -d '{"email":"x@example.com","name":"X"}'` → 201。`make test && make lint` → PASS。
- [ ] **Step 5: Commit** `git add -A && git commit -m "feat(impl): implement handlers via ORM and forbid raw SQL"`

---

### Task 8: ORM ベース seeder

**Files:** Create `seeds/__init__.py`, `seeds/run.py`, `seeds/e2e.py`; Modify `Makefile`

**Interfaces:** Produces CLI `python -m seeds.run --profile e2e` (全テーブルを依存逆順で削除 → ORM オブジェクトを投入, 1 トランザクション)。e2e 用固定データ: users `alice@example.com`(Alice), `bob@example.com`(Bob); tags `python`, `orm`, `fastapi`; posts `SQLAlchemy入門`(alice, published, [python, orm]), `下書き`(alice, unpublished, []), `FastAPIでAPI`(bob, published, [python, fastapi])。

- [ ] **Step 1: `seeds/e2e.py`**

```python
"""Playwright e2e 用の固定データ。生成モデルを使うので、スキーマ変更時は型/属性エラーで気付ける。"""

from app.generated.db.models import Post, Tag, User


def build() -> list[object]:
    python, orm, fastapi = Tag(name="python"), Tag(name="orm"), Tag(name="fastapi")
    alice = User(email="alice@example.com", name="Alice")
    bob = User(email="bob@example.com", name="Bob")
    alice.posts = [
        Post(title="SQLAlchemy入門", body="ORM の基本", published=True, tags=[python, orm]),
        Post(title="下書き", body="未公開", published=False, tags=[]),
    ]
    bob.posts = [Post(title="FastAPIでAPI", body="OpenAPI 駆動", published=True, tags=[python, fastapi])]
    return [alice, bob, python, orm, fastapi]
```

- [ ] **Step 2: `seeds/run.py`**

```python
"""python -m seeds.run --profile e2e"""

import argparse
from collections.abc import Callable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.generated.db.models import Base
from seeds import e2e

PROFILES: dict[str, Callable[[], list[object]]] = {"e2e": e2e.build}


def reset(session: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(delete(table))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="seeds.run")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="e2e")
    args = parser.parse_args(argv)
    objects = PROFILES[args.profile]()
    with SessionLocal() as session, session.begin():
        reset(session)
        session.add_all(objects)
    print(f"seeded profile={args.profile} objects={len(objects)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3:** Makefile: `seed: ; $(COMPOSE) exec -T api python -m seeds.run --profile e2e`。`make up && make seed` → `seeded profile=e2e objects=5`、`curl -s 'localhost:8000/posts?tag=orm'` → `SQLAlchemy入門` 1 件。2 回目の `make seed` も成功 (冪等)。`make test` (no_raw_sql が seeds も検査) → PASS。
- [ ] **Step 4: Commit** `git add -A && git commit -m "feat(seeds): ORM-based seeder for e2e data"`

---

### Task 9: Playwright API テスト + OpenAPI → TS 型生成

**Files:** Create `e2e/package.json`, `e2e/package-lock.json`(npm install で生成), `e2e/tsconfig.json`, `e2e/playwright.config.ts`, `e2e/global-setup.ts`, `e2e/tests/health.spec.ts`, `e2e/tests/users.spec.ts`, `e2e/tests/posts.spec.ts`; 生成 `e2e/generated/api.d.ts`; Modify `Makefile`

**Interfaces:** Consumes Task 8 の固定データ、`http://localhost:8000`。Produces `components["schemas"][...]` 型 (openapi-typescript)。

- [ ] **Step 1: `e2e/package.json`**

```json
{
  "name": "python-orm-sample-e2e",
  "private": true,
  "scripts": {
    "test": "playwright test",
    "gen:types": "openapi-typescript ../openapi/openapi.yaml -o generated/api.d.ts"
  },
  "devDependencies": {
    "@playwright/test": "1.48.2",
    "@types/node": "22.7.5",
    "openapi-typescript": "7.4.1",
    "typescript": "5.6.3"
  }
}
```

`cd e2e && npm install` で lock 生成 (API テストのみなのでブラウザの `playwright install` は不要)。

- [ ] **Step 2: `e2e/tsconfig.json`**

```json
{ "compilerOptions": { "target": "ES2022", "module": "commonjs", "strict": true, "esModuleInterop": true, "types": ["node"] } }
```

- [ ] **Step 3: `e2e/playwright.config.ts`**

```ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.ts",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.API_BASE_URL ?? "http://localhost:8000",
    extraHTTPHeaders: { Accept: "application/json" },
  },
});
```

- [ ] **Step 4: `e2e/global-setup.ts`** (seeder で DB を既知状態に)

```ts
import { execSync } from "node:child_process";
import path from "node:path";

export default async function globalSetup(): Promise<void> {
  const root = path.resolve(__dirname, "..");
  execSync("docker compose exec -T api python -m seeds.run --profile e2e", { cwd: root, stdio: "inherit" });
}
```

- [ ] **Step 5: テスト (先に書いて、`make generate` 前は型 import で失敗することを確認)**

`e2e/tests/health.spec.ts`
```ts
import { expect, test } from "@playwright/test";

test("GET /health は ok", async ({ request }) => {
  const res = await request.get("/health");
  expect(res.status()).toBe(200);
  expect(await res.json()).toEqual({ status: "ok" });
});

test("GET /openapi.json は仕様ファイルを返す", async ({ request }) => {
  const spec = await (await request.get("/openapi.json")).json();
  expect(spec.info.title).toBe("python-orm-sample API");
});
```

`e2e/tests/users.spec.ts`
```ts
import { expect, test } from "@playwright/test";
import type { components } from "../generated/api";

type User = components["schemas"]["User"];

test("GET /users は seed ユーザーを含む", async ({ request }) => {
  const res = await request.get("/users");
  expect(res.status()).toBe(200);
  const users: User[] = await res.json();
  expect(users.map((u) => u.email)).toEqual(expect.arrayContaining(["alice@example.com", "bob@example.com"]));
});

test("POST /users → GET /users/{user_id}", async ({ request }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const created = await request.post("/users", { data: { email, name: "E2E" } });
  expect(created.status()).toBe(201);
  const user: User = await created.json();
  const fetched = await request.get(`/users/${user.id}`);
  expect(fetched.status()).toBe(200);
  expect(await fetched.json()).toEqual(user);
});

test("POST /users の email 重複は 409", async ({ request }) => {
  const res = await request.post("/users", { data: { email: "alice@example.com", name: "dup" } });
  expect(res.status()).toBe(409);
});

test("存在しないユーザーは 404", async ({ request }) => {
  expect((await request.get("/users/999999")).status()).toBe(404);
});

test("limit=0 はバリデーションエラー 422", async ({ request }) => {
  expect((await request.get("/users?limit=0")).status()).toBe(422);
});
```

`e2e/tests/posts.spec.ts`
```ts
import { expect, test } from "@playwright/test";
import type { components } from "../generated/api";

type Post = components["schemas"]["Post"];
type User = components["schemas"]["User"];

async function alice(request: import("@playwright/test").APIRequestContext): Promise<User> {
  const users: User[] = await (await request.get("/users?limit=100")).json();
  return users.find((u) => u.email === "alice@example.com")!;
}

test("GET /posts?tag=orm は seed の投稿を返す", async ({ request }) => {
  const posts: Post[] = await (await request.get("/posts?tag=orm")).json();
  expect(posts.map((p) => p.title)).toContain("SQLAlchemy入門");
  for (const p of posts) expect(p.tags.map((t) => t.name)).toContain("orm");
});

test("POST /posts → GET → DELETE → 404", async ({ request }) => {
  const author = await alice(request);
  const tag = `e2e-${Date.now()}`;
  const created = await request.post("/posts", {
    data: { author_id: author.id, title: "E2E 投稿", body: "本文", tag_names: [tag, tag] },
  });
  expect(created.status()).toBe(201);
  const post: Post = await created.json();
  expect(post.published).toBe(false);
  expect(post.tags.map((t) => t.name)).toEqual([tag]);

  expect((await request.get(`/posts/${post.id}`)).status()).toBe(200);
  expect((await request.delete(`/posts/${post.id}`)).status()).toBe(204);
  expect((await request.get(`/posts/${post.id}`)).status()).toBe(404);
});

test("存在しない author は 400", async ({ request }) => {
  const res = await request.post("/posts", { data: { author_id: 999999, title: "x", body: "y" } });
  expect(res.status()).toBe(400);
});

test("GET /tags は seed タグを含む", async ({ request }) => {
  const tags = await (await request.get("/tags")).json();
  expect(tags.map((t: { name: string }) => t.name)).toEqual(expect.arrayContaining(["fastapi", "orm", "python"]));
});
```

- [ ] **Step 6:** Makefile の `generate` に TS 型生成を追加し、`e2e` を追加:

```make
generate:
	$(TOOLS) python -m codegen all
	npm --prefix e2e run --silent gen:types

.PHONY: e2e
e2e:
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) up -d --build --wait db api
	npm --prefix e2e test
```

- [ ] **Step 7:** `make generate && make e2e` → 全テスト PASS。
- [ ] **Step 8: Commit** `git add -A && git commit -m "test(e2e): playwright API tests against containerized API with seeded data"`

---

### Task 10: ガードレール (生成物整合チェック / pre-commit / Claude Code フック / CI / CLAUDE.md)

**Files:** Create `.claude/hooks/guard.py`, `.claude/settings.json`, `tests/test_guard_hook.py`, `.githooks/pre-commit`, `.github/workflows/ci.yml`, `CLAUDE.md`; Modify `Makefile`

**Interfaces:** Produces make `check-generated`, `check`, `setup`; フックは stdin の PreToolUse JSON (`tool_name`, `tool_input.file_path|notebook_path|command`) を読み、拒否時は exit 2 + stderr。

- [ ] **Step 1: 失敗するテスト `tests/test_guard_hook.py`**

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "guard.py"


def run(tool: str, **tool_input: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    return subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True)


@pytest.mark.parametrize(
    "rel",
    ["app/impl/handlers.py", "openapi/openapi.yaml", "schema/schema.yaml", "seeds/e2e.py",
     "e2e/tests/users.spec.ts", "tests/impl/test_x.py", "docs/notes.md", "README.md"],
)
def test_allows_ai_writable(rel):
    assert run("Edit", file_path=str(ROOT / rel)).returncode == 0


@pytest.mark.parametrize(
    "rel",
    ["app/generated/db/models.py", "app/generated/api/routers.py", "migrations/versions/x.py",
     "migrations/env.py", "codegen/models_gen.py", ".claude/settings.json", "docs/er/schema.md",
     "e2e/generated/api.d.ts", "app/main.py", "app/core/db.py", "Makefile", "CLAUDE.md",
     "tests/test_contract.py", "app/impl/../generated/db/models.py"],
)
def test_denies_protected(rel):
    r = run("Write", file_path=str(ROOT / rel))
    assert r.returncode == 2
    assert "make generate" in r.stderr


def test_notebook_path_is_checked():
    assert run("NotebookEdit", notebook_path=str(ROOT / "codegen/x.ipynb")).returncode == 2


def test_outside_repo_is_not_our_concern(tmp_path):
    assert run("Write", file_path=str(tmp_path / "x.txt")).returncode == 0


@pytest.mark.parametrize(
    "cmd",
    ["sed -i s/a/b/ app/generated/db/models.py", "echo x > codegen/a.py", "rm -rf migrations/versions",
     "cp /tmp/x.py app/generated/api/routers.py", "git commit --no-verify -m x",
     "git config core.hooksPath /dev/null", "python -c 'open(\"app/main.py\",\"w\")'"],
)
def test_denies_mutating_bash(cmd):
    assert run("Bash", command=cmd).returncode == 2


@pytest.mark.parametrize(
    "cmd",
    ["make generate", "cat app/generated/db/models.py", "git diff app/generated",
     "sed -i s/a/b/ app/impl/handlers.py", "ls migrations/versions 2>/dev/null"],
)
def test_allows_safe_bash(cmd):
    assert run("Bash", command=cmd).returncode == 0
```

- [ ] **Step 2:** `make test` → FAIL
- [ ] **Step 3: `.claude/hooks/guard.py`** (stdlib のみ)

```python
#!/usr/bin/env python3
"""Claude Code PreToolUse フック: AI の書き込み先を allowlist で制限する.

AI が触ってよいのは「仕様」と「中身」だけ。ORM モデル・API のガワ・マイグレーション・ER 図・
ジェネレータ・配線・ガードレール自身は機械生成 or 人間管理。
Bash 判定はベストエフォートで、最終防衛線は pre-commit / CI の `make check` (再生成して差分検出)。
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2]).resolve()

ALLOWED_PREFIXES = ("schema/", "openapi/", "app/impl/", "seeds/", "tests/impl/", "e2e/tests/", "docs/")
ALLOWED_FILES = ("README.md",)
DENIED_PREFIXES = ("docs/er/",)

MUTATING = re.compile(
    r"(^|[\s;&|(])(rm|mv|cp|tee|truncate|touch|ln|install|chmod|patch|dd)\s"
    r"|sed\s+(-[a-zA-Z]*i|--in-place)"
    r"|perl\s+-[a-zA-Z]*i"
    r"|(?<![0-9&])>"
    r"|git\s+(checkout|restore|apply|am|stash|mv|rm)\b"
    r"|python3?\s+-c"
)
ALWAYS_DENY = re.compile(r"--no-verify|core\.hooksPath")

MESSAGE = (
    "このパスは自動生成物・ジェネレータ・配線のため AI は編集できません: {path}\n"
    "変更したい場合は仕様 (schema/schema.yaml, openapi/openapi.yaml) を編集し `make generate` "
    "(スキーマ変更時は続けて `make migration m=\"...\"`) を実行してください。"
    "ジェネレータ自体の変更が必要なら人間に依頼してください。"
)


def rel_in_repo(raw: str) -> str | None:
    p = Path(raw)
    p = (p if p.is_absolute() else ROOT / p).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return None


def writable(rel: str) -> bool:
    if any(rel.startswith(d) for d in DENIED_PREFIXES):
        return False
    return rel in ALLOWED_FILES or any(rel.startswith(a) for a in ALLOWED_PREFIXES)


def deny(path: str) -> int:
    print(MESSAGE.format(path=path), file=sys.stderr)
    return 2


def check_bash(command: str) -> int:
    if ALWAYS_DENY.search(command):
        print("git フックの回避 (--no-verify / core.hooksPath 変更) は禁止です。", file=sys.stderr)
        return 2
    if not MUTATING.search(command):
        return 0
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    for token in tokens:
        for piece in re.split(r"[\s'\"(),=]+", token.lstrip(">")):
            if not piece:
                continue
            first = piece.removeprefix("./").split("/")[0]
            if not (Path(piece).is_absolute() or (ROOT / first).exists()):
                continue
            rel = rel_in_repo(piece)
            if rel is not None and rel != "" and rel != "." and not writable(rel):
                return deny(rel)
    return 0


def main() -> int:
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if tool == "Bash":
        return check_bash(tool_input.get("command", ""))
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw:
        return 0
    rel = rel_in_repo(raw)
    if rel is None or writable(rel):
        return 0
    return deny(rel)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: `.claude/settings.json`** (フック + 二重の permission deny)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write|NotebookEdit|Bash",
        "hooks": [{ "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py\"" }]
      }
    ]
  },
  "permissions": {
    "deny": [
      "Edit(app/generated/**)", "Edit(app/core/**)", "Edit(app/main.py)",
      "Edit(migrations/**)", "Edit(codegen/**)", "Edit(docs/er/**)", "Edit(e2e/generated/**)",
      "Edit(.claude/**)", "Edit(.githooks/**)", "Edit(.github/**)", "Edit(CLAUDE.md)",
      "Edit(Makefile)", "Edit(Dockerfile)", "Edit(docker-compose.yml)", "Edit(pyproject.toml)",
      "Edit(alembic.ini)", "Bash(git commit --no-verify:*)"
    ]
  }
}
```

- [ ] **Step 5:** Makefile に追記:

```make
GENERATED := app/generated docs/er e2e/generated

.PHONY: check-generated check setup
check-generated: generate
	@git diff --exit-code -- $(GENERATED) \
	  || (echo "NG: 生成物が仕様と一致しません。生成物を直接編集せず、仕様を直して make generate してください" && exit 1)
	@test -z "$$(git ls-files --others --exclude-standard -- $(GENERATED))" \
	  || (echo "NG: 未追跡の生成物があります (git add してください)" && exit 1)
check: check-generated lint test check-migrations
setup:
	git config core.hooksPath .githooks
	npm --prefix e2e ci
```

- [ ] **Step 6: `.githooks/pre-commit`** (`chmod +x`)

```sh
#!/bin/sh
# 生成物の手編集・仕様との不整合・マイグレーション改ざんをコミット前に検出する
set -e
make check-generated
make lint
docker compose run --rm --no-deps tools python -m codegen checksum-verify
```

- [ ] **Step 7: `.github/workflows/ci.yml`**

```yaml
name: ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: e2e/package-lock.json }
      - run: npm --prefix e2e ci
      - run: make build
      - run: make check
      - run: make e2e
```

- [ ] **Step 8: `CLAUDE.md`**

```markdown
# AI 作業ルール (このリポジトリ)

## 編集してよいもの
- 仕様: `schema/schema.yaml` (DB), `openapi/openapi.yaml` (API)
- 中身: `app/impl/` (ApiHandlers の実装), `seeds/`, `tests/impl/`, `e2e/tests/`, `docs/` (docs/er を除く), `README.md`

## 編集してはいけないもの (フックでブロックされます)
`app/generated/`, `migrations/`, `docs/er/`, `e2e/generated/`, `codegen/`, `app/core/`, `app/main.py`, `.claude/`, `.githooks/`, `.github/`, ビルド設定類。
生成物を直したくなったら **仕様を直して再生成** する。ジェネレータが仕様を表現できない場合は人間に相談する。

## 手順
1. DB 変更: `schema/schema.yaml` を編集 → `make generate` → `make migration m="内容"`
2. API 変更: `openapi/openapi.yaml` を編集 → `make generate` → 起動時/`make test` が未実装 operation を指摘するので `app/impl/handlers.py` に実装
3. 確認: `make check` → `make e2e`

## 実装ルール
- DB アクセスは `app.generated.db.models` の ORM モデル経由のみ。`text()` / `exec_driver_sql` / SQL 文字列の `execute` は禁止 (ruff TID251 とテストで検出)。
- `git commit --no-verify` 禁止。
```

- [ ] **Step 9:** `make test` → PASS (guard テスト含む)。`make setup && make check` → PASS。改ざん検証: `echo "# x" >> app/generated/db/models.py && make check-generated` → NG で失敗 → `make generate` で復旧。
- [ ] **Step 10: Commit** `git add -A && git commit -m "feat(guardrails): claude hook allowlist, regenerate-and-diff checks, pre-commit and CI"`

---

### Task 11: README

**Files:** Modify `README.md`

- [ ] **Step 1:** README に以下を記載: 構成図 (SoT → 生成物の流れ, テキスト図)、ディレクトリと「誰が編集するか」の表、コマンド一覧 (`make build / generate / migration m= / migrate / up / seed / test / lint / check / e2e / setup`)、ER 図へのリンク (`docs/er/schema.md`)、Flask-Migrate ではなく Alembic 直利用の理由、ガードレールの多層構造 (Claude フック → pre-commit → CI) と Bash 判定がベストエフォートである旨。
- [ ] **Step 2: Commit** `git commit -am "docs: usage and architecture"`

---

## Verification (end-to-end)

1. `make setup && make build`
2. `make check` — 生成物が仕様と一致 / ruff (生 SQL 禁止含む) / pytest (codegen・契約・ガードフック・生 SQL 検査) / マイグレーションのチェックサムと `alembic check`
3. `make e2e` — compose で db+api を起動し、globalSetup で seeder 投入、Playwright が `http://localhost:8000` に実アクセスして全件 PASS
4. 仕様駆動フローの通し確認: `schema/schema.yaml` の users に `bio: {type: text, nullable: true}` を追加 → `make generate` → `make migration m="add bio"` → 新マイグレーション・`docs/er/schema.md` 更新・`migrations/checksums.txt` 更新を確認 → `make check-migrations` PASS → 変更を破棄 (`git checkout . && git clean -fd migrations`)
5. ガード確認: Claude Code から `app/generated/db/models.py` を Edit しようとしてブロックされること、`app/impl/handlers.py` は編集できること

## Execution Handoff

承認後の実行方式 (選択):
1. **Subagent-Driven (推奨)** — superpowers:subagent-driven-development でタスクごとに新規サブエージェント + タスク間レビュー
2. **Inline Execution** — superpowers:executing-plans でこのセッション内でチェックポイント付き一括実行
