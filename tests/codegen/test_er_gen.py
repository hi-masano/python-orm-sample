from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

from codegen import er_gen


def test_render_mermaid():
    md = MetaData()
    Table(
        "users",
        md,
        Column("id", Integer, primary_key=True),
        Column("email", String(255), unique=True),
    )
    Table(
        "posts",
        md,
        Column("id", Integer, primary_key=True),
        Column("author_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("editor_id", Integer, ForeignKey("users.id"), nullable=True),
    )
    out = er_gen.render(md)
    assert out.startswith("erDiagram\n")
    assert '    users {\n        INTEGER id PK "not null"\n        VARCHAR(255) email UK' in out
    assert '    users ||--o{ posts : "author_id"' in out
    assert '    users |o--o{ posts : "editor_id"' in out
    assert out == er_gen.render(md)
