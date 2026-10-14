import copy
import sys
import types

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
            "relationships": {
                "posts": {"target": "posts", "many": True, "back_populates": "author"}
            },
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
        (
            lambda d: d["tables"]["posts"]["columns"]["author_id"].update(foreign_key="nope.id"),
            "参照先",
        ),
        (
            lambda d: d["tables"]["posts"]["relationships"]["author"].update(target="ghosts"),
            "target",
        ),
        (
            lambda d: d["tables"]["posts"]["relationships"]["author"].update(back_populates="x"),
            "back_populates",
        ),
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
    mod = types.ModuleType("generated_models_under_test")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(first, "models.py", "exec"), mod.__dict__)
        users = mod.Base.metadata.tables["users"]
        posts = mod.Base.metadata.tables["posts"]
        assert users.c.email.unique is True
        assert users.c.email.type.length == 255
        assert posts.c.note.nullable is True
        assert posts.c.author_id.nullable is False
        fk = next(iter(posts.c.author_id.foreign_keys))
        assert fk.target_fullname == "users.id" and fk.ondelete == "CASCADE"
        assert users.comment == "利用者"
    finally:
        sys.modules.pop(mod.__name__, None)
