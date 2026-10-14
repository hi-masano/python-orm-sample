# このファイルは自動生成されています。直接編集しないでください (DO NOT EDIT).
# source: openapi/openapi.yaml (sha256: 0633f0645e036e1f)
# regenerate: make generate

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, EmailStr, Field, RootModel


class Health(BaseModel):
    status: str


class Error(BaseModel):
    detail: str


class User(BaseModel):
    id: int
    email: EmailStr
    name: str
    created_at: AwareDatetime


class UserCreate(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    name: str = Field(..., max_length=100, min_length=1)


class Tag(BaseModel):
    id: int
    name: str


class Post(BaseModel):
    id: int
    author_id: int
    title: str
    body: str
    published: bool
    tags: list[Tag]
    created_at: AwareDatetime


class TagName(RootModel[str]):
    root: str = Field(..., max_length=50, min_length=1)


class PostCreate(BaseModel):
    author_id: int
    title: str = Field(..., max_length=200, min_length=1)
    body: str
    published: bool = False
    tag_names: list[TagName] = Field([], validate_default=True)
