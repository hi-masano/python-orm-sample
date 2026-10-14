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

ALLOWED_PREFIXES = (
    "schema/",
    "openapi/",
    "app/impl/",
    "seeds/",
    "tests/impl/",
    "e2e/tests/",
    "docs/",
    ".superpowers/",
)
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
    '(スキーマ変更時は続けて `make migration m="..."`) を実行してください。'
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
