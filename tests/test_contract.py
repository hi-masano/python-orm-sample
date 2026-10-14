from pathlib import Path

import yaml
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.impl.handlers import Handlers
from app.main import app

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi/openapi.yaml"
SPEC = yaml.safe_load(SPEC_PATH.read_text("utf-8"))
METHODS = {"get", "post", "put", "patch", "delete"}


def _api_routes(routes):
    # FastAPI 0.143+ は include_router を遅延展開 (_IncludedRouter) するため original_router を辿る
    for r in routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "original_router"):
            yield from _api_routes(r.original_router.routes)


def test_routes_match_spec():
    expected = {
        (m.upper(), path, op["operationId"])
        for path, item in SPEC["paths"].items()
        for m, op in item.items()
        if m in METHODS
    }
    actual = {(m, r.path, r.operation_id) for r in _api_routes(app.routes) for m in r.methods}
    assert actual == expected


def test_impl_implements_every_operation():
    assert not Handlers.__abstractmethods__


def test_served_openapi_is_the_spec_file():
    assert TestClient(app).get("/openapi.json").json() == SPEC
