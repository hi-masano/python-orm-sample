from sqlalchemy.orm import Session

from app.generated.api import schemas
from app.generated.api.handlers import ApiHandlers


class Handlers(ApiHandlers):
    def __init__(self, session: Session) -> None:
        self.session = session

    def health_check(self) -> schemas.Health:
        raise NotImplementedError

    def list_users(self, *, limit: int, offset: int) -> list[schemas.User]:
        raise NotImplementedError

    def create_user(self, *, body: schemas.UserCreate) -> schemas.User:
        raise NotImplementedError

    def get_user(self, *, user_id: int) -> schemas.User:
        raise NotImplementedError

    def list_posts(self, *, tag: str | None, author_id: int | None) -> list[schemas.Post]:
        raise NotImplementedError

    def create_post(self, *, body: schemas.PostCreate) -> schemas.Post:
        raise NotImplementedError

    def get_post(self, *, post_id: int) -> schemas.Post:
        raise NotImplementedError

    def delete_post(self, *, post_id: int) -> None:
        raise NotImplementedError

    def list_tags(self) -> list[schemas.Tag]:
        raise NotImplementedError
