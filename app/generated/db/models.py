# このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT).
# source: schema/schema.yaml (sha256: ce304028acee0d9f)
# regenerate: make generate

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    false,
    func,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer(), ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer(), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    comment="posts と tags の中間テーブル",
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "利用者"}

    id: Mapped[int] = mapped_column(Integer(), primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="ログイン用メールアドレス"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    posts: Mapped[list[Post]] = relationship("Post", back_populates="author")


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {"comment": "投稿"}

    id: Mapped[int] = mapped_column(Integer(), primary_key=True)
    author_id: Mapped[int] = mapped_column(
        Integer(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    published: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    author: Mapped[User] = relationship("User", back_populates="posts")
    tags: Mapped[list[Tag]] = relationship("Tag", secondary="post_tags", back_populates="posts")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = {"comment": "タグ"}

    id: Mapped[int] = mapped_column(Integer(), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    posts: Mapped[list[Post]] = relationship("Post", secondary="post_tags", back_populates="tags")
