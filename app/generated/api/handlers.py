# このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT).
# source: openapi/openapi.yaml (sha256: 0633f0645e036e1f)
# regenerate: make generate

from __future__ import annotations

from abc import ABC, abstractmethod

from app.generated.api import schemas


class ApiHandlers(ABC):
    """OpenAPI の各 operation に 1:1 対応する実装インターフェース.

    実装は app/impl/handlers.py の Handlers クラスで行う。
    """

    @abstractmethod
    def health_check(self) -> schemas.Health:
        """GET /health — ヘルスチェック"""

    @abstractmethod
    def list_users(self, *, limit: int, offset: int) -> list[schemas.User]:
        """GET /users — ユーザー一覧"""

    @abstractmethod
    def create_user(self, *, body: schemas.UserCreate) -> schemas.User:
        """POST /users — ユーザー作成"""

    @abstractmethod
    def get_user(self, *, user_id: int) -> schemas.User:
        """GET /users/{user_id} — ユーザー取得"""

    @abstractmethod
    def list_posts(self, *, tag: str | None, author_id: int | None) -> list[schemas.Post]:
        """GET /posts — 投稿一覧"""

    @abstractmethod
    def create_post(self, *, body: schemas.PostCreate) -> schemas.Post:
        """POST /posts — 投稿作成"""

    @abstractmethod
    def get_post(self, *, post_id: int) -> schemas.Post:
        """GET /posts/{post_id} — 投稿取得"""

    @abstractmethod
    def delete_post(self, *, post_id: int) -> None:
        """DELETE /posts/{post_id} — 投稿削除"""

    @abstractmethod
    def list_tags(self) -> list[schemas.Tag]:
        """GET /tags — タグ一覧"""
