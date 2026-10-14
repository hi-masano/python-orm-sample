"""OpenAPI operation の実装。DB アクセスは ORM モデル経由のみ (生 SQL 禁止)。"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.generated.api import schemas
from app.generated.api.handlers import ApiHandlers
from app.generated.db import models


class Handlers(ApiHandlers):
    def __init__(self, session: Session) -> None:
        self.session = session

    def health_check(self) -> schemas.Health:
        return schemas.Health(status="ok")

    def list_users(self, *, limit: int, offset: int) -> list[schemas.User]:
        stmt = select(models.User).order_by(models.User.id).limit(limit).offset(offset)
        rows = self.session.scalars(stmt)
        return [schemas.User.model_validate(u, from_attributes=True) for u in rows]

    def create_user(self, *, body: schemas.UserCreate) -> schemas.User:
        exists = self.session.scalar(select(models.User).where(models.User.email == body.email))
        if exists is not None:
            raise HTTPException(status_code=409, detail="email already exists")
        user = models.User(email=body.email, name=body.name)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return schemas.User.model_validate(user, from_attributes=True)

    def get_user(self, *, user_id: int) -> schemas.User:
        user = self.session.get(models.User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        return schemas.User.model_validate(user, from_attributes=True)

    def list_posts(self, *, tag: str | None, author_id: int | None) -> list[schemas.Post]:
        stmt = select(models.Post).options(selectinload(models.Post.tags)).order_by(models.Post.id)
        if tag is not None:
            stmt = stmt.where(models.Post.tags.any(models.Tag.name == tag))
        if author_id is not None:
            stmt = stmt.where(models.Post.author_id == author_id)
        rows = self.session.scalars(stmt)
        return [schemas.Post.model_validate(p, from_attributes=True) for p in rows]

    def create_post(self, *, body: schemas.PostCreate) -> schemas.Post:
        if self.session.get(models.User, body.author_id) is None:
            raise HTTPException(status_code=400, detail="author not found")
        names = dict.fromkeys(t.root for t in body.tag_names)
        tags = [self._get_or_create_tag(name) for name in names]
        post = models.Post(
            author_id=body.author_id,
            title=body.title,
            body=body.body,
            published=body.published,
            tags=tags,
        )
        self.session.add(post)
        self.session.commit()
        self.session.refresh(post)
        return schemas.Post.model_validate(post, from_attributes=True)

    def get_post(self, *, post_id: int) -> schemas.Post:
        return schemas.Post.model_validate(self._post_or_404(post_id), from_attributes=True)

    def delete_post(self, *, post_id: int) -> None:
        self.session.delete(self._post_or_404(post_id))
        self.session.commit()

    def list_tags(self) -> list[schemas.Tag]:
        stmt = select(models.Tag).order_by(models.Tag.name)
        rows = self.session.scalars(stmt)
        return [schemas.Tag.model_validate(t, from_attributes=True) for t in rows]

    def _post_or_404(self, post_id: int) -> models.Post:
        post = self.session.get(models.Post, post_id, options=[selectinload(models.Post.tags)])
        if post is None:
            raise HTTPException(status_code=404, detail="post not found")
        return post

    def _get_or_create_tag(self, name: str) -> models.Tag:
        tag = self.session.scalar(select(models.Tag).where(models.Tag.name == name))
        return tag if tag is not None else models.Tag(name=name)
