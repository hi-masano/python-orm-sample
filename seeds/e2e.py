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
    bob.posts = [
        Post(title="FastAPIでAPI", body="OpenAPI 駆動", published=True, tags=[python, fastapi]),
    ]
    return [alice, bob, python, orm, fastapi]
