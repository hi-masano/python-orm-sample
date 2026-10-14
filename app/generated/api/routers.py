# このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT).
# source: openapi/openapi.yaml (sha256: 0633f0645e036e1f)
# regenerate: make generate

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Response

from app.generated.api import schemas
from app.generated.api.handlers import ApiHandlers


def build_router(get_handlers: Callable[..., ApiHandlers]) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/health",
        operation_id="healthCheck",
        status_code=200,
        response_model=schemas.Health,
        tags=["system"],
        summary="ヘルスチェック",
    )
    def health_check(
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> schemas.Health:
        return handlers.health_check()

    @router.get(
        "/users",
        operation_id="listUsers",
        status_code=200,
        response_model=list[schemas.User],
        tags=["users"],
        summary="ユーザー一覧",
    )
    def list_users(
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[schemas.User]:
        return handlers.list_users(limit=limit, offset=offset)

    @router.post(
        "/users",
        operation_id="createUser",
        status_code=201,
        response_model=schemas.User,
        tags=["users"],
        summary="ユーザー作成",
    )
    def create_user(
        body: Annotated[schemas.UserCreate, Body()],
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> schemas.User:
        return handlers.create_user(body=body)

    @router.get(
        "/users/{user_id}",
        operation_id="getUser",
        status_code=200,
        response_model=schemas.User,
        tags=["users"],
        summary="ユーザー取得",
    )
    def get_user(
        user_id: Annotated[int, Path()],
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> schemas.User:
        return handlers.get_user(user_id=user_id)

    @router.get(
        "/posts",
        operation_id="listPosts",
        status_code=200,
        response_model=list[schemas.Post],
        tags=["posts"],
        summary="投稿一覧",
    )
    def list_posts(
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
        tag: Annotated[str | None, Query()] = None,
        author_id: Annotated[int | None, Query()] = None,
    ) -> list[schemas.Post]:
        return handlers.list_posts(tag=tag, author_id=author_id)

    @router.post(
        "/posts",
        operation_id="createPost",
        status_code=201,
        response_model=schemas.Post,
        tags=["posts"],
        summary="投稿作成",
    )
    def create_post(
        body: Annotated[schemas.PostCreate, Body()],
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> schemas.Post:
        return handlers.create_post(body=body)

    @router.get(
        "/posts/{post_id}",
        operation_id="getPost",
        status_code=200,
        response_model=schemas.Post,
        tags=["posts"],
        summary="投稿取得",
    )
    def get_post(
        post_id: Annotated[int, Path()],
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> schemas.Post:
        return handlers.get_post(post_id=post_id)

    @router.delete(
        "/posts/{post_id}",
        operation_id="deletePost",
        status_code=204,
        response_model=None,
        tags=["posts"],
        summary="投稿削除",
    )
    def delete_post(
        post_id: Annotated[int, Path()],
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> Response:
        handlers.delete_post(post_id=post_id)
        return Response(status_code=204)

    @router.get(
        "/tags",
        operation_id="listTags",
        status_code=200,
        response_model=list[schemas.Tag],
        tags=["tags"],
        summary="タグ一覧",
    )
    def list_tags(
        handlers: Annotated[ApiHandlers, Depends(get_handlers)],
    ) -> list[schemas.Tag]:
        return handlers.list_tags()

    return router
