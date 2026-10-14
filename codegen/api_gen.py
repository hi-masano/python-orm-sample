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
CONSTRAINTS = {
    "minimum": "ge",
    "maximum": "le",
    "minLength": "min_length",
    "maxLength": "max_length",
}
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
        name = ref[len(REF_PREFIX) :]
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
            raw_params = [*item.get("parameters", []), *op.get("parameters", [])]
            params = tuple(_param(p, where) for p in raw_params)
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
            ops.append(
                Operation(
                    operation_id=op_id,
                    func_name=to_snake(op_id),
                    method=method,
                    path=path,
                    status_code=status,
                    response_type=response_type,
                    body_type=body_type,
                    params=params,
                    tags=tuple(op.get("tags", [])),
                    summary=op.get("summary"),
                )
            )
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
            "--input",
            str(src),
            "--input-file-type",
            "openapi",
            "--output",
            str(schemas_py),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.12",
            "--use-standard-collections",
            "--use-union-operator",
            "--field-constraints",
            "--disable-timestamp",
            "--custom-file-header",
            hdr.rstrip("\n"),
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
