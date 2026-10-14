import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "guard.py"


def run(tool: str, **tool_input: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    return subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    "rel",
    [
        "app/impl/handlers.py",
        "openapi/openapi.yaml",
        "schema/schema.yaml",
        "seeds/e2e.py",
        "e2e/tests/users.spec.ts",
        "tests/impl/test_x.py",
        "docs/notes.md",
        "README.md",
        ".superpowers/sdd/x/progress.md",
    ],
)
def test_allows_ai_writable(rel):
    assert run("Edit", file_path=str(ROOT / rel)).returncode == 0


@pytest.mark.parametrize(
    "rel",
    [
        "app/generated/db/models.py",
        "app/generated/api/routers.py",
        "migrations/versions/x.py",
        "migrations/env.py",
        "codegen/models_gen.py",
        ".claude/settings.json",
        "docs/er/schema.md",
        "e2e/generated/api.d.ts",
        "app/main.py",
        "app/core/db.py",
        "Makefile",
        "CLAUDE.md",
        "tests/test_contract.py",
        "app/impl/../generated/db/models.py",
    ],
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
    [
        "sed -i s/a/b/ app/generated/db/models.py",
        "echo x > codegen/a.py",
        "rm -rf migrations/versions",
        "cp /tmp/x.py app/generated/api/routers.py",
        "git commit --no-verify -m x",
        "git config core.hooksPath /dev/null",
        'python -c \'open("app/main.py","w")\'',
    ],
)
def test_denies_mutating_bash(cmd):
    assert run("Bash", command=cmd).returncode == 2


@pytest.mark.parametrize(
    "cmd",
    [
        "make generate",
        "cat app/generated/db/models.py",
        "git diff app/generated",
        "sed -i s/a/b/ app/impl/handlers.py",
        "ls migrations/versions 2>/dev/null",
        "echo x >> .superpowers/sdd/x/progress.md",
    ],
)
def test_allows_safe_bash(cmd):
    assert run("Bash", command=cmd).returncode == 0
