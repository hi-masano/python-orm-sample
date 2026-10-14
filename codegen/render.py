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
