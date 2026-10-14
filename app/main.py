"""配線のみ。生成ルータに実装 (app/impl) を注入する。"""

from pathlib import Path
from typing import Annotated

import yaml
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.generated.api.routers import build_router
from app.impl.handlers import Handlers

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi" / "openapi.yaml"


def get_handlers(session: Annotated[Session, Depends(get_session)]) -> Handlers:
    return Handlers(session)


def create_app() -> FastAPI:
    if missing := sorted(Handlers.__abstractmethods__):
        raise RuntimeError(f"app/impl/handlers.py に未実装の operation があります: {missing}")
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    app = FastAPI(title=spec["info"]["title"], version=spec["info"]["version"])
    app.include_router(build_router(get_handlers))
    app.openapi = lambda: spec  # 公開する OpenAPI は仕様ファイルそのもの
    return app


app = create_app()
