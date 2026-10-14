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
