import copy

import pytest

from codegen import api_gen
from codegen.render import CodegenError

ITEM = {"$ref": "#/components/schemas/Item"}
ITEM_CREATE = {"$ref": "#/components/schemas/ItemCreate"}


ITEM_ID = {"name": "item_id", "in": "path", "required": True, "schema": {"type": "integer"}}


def _json(schema):
    return {"content": {"application/json": {"schema": schema}}}


SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "t", "version": "1"},
    "paths": {
        "/items/{item_id}": {
            "get": {
                "operationId": "getItem",
                "parameters": [
                    ITEM_ID,
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 20, "minimum": 1},
                    },
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": {200: _json(ITEM)},
            },
            "delete": {
                "operationId": "deleteItem",
                "parameters": [ITEM_ID],
                "responses": {"204": {"description": "deleted"}},
            },
        },
        "/items": {
            "post": {
                "operationId": "createItem",
                "requestBody": _json(ITEM_CREATE),
                "responses": {"201": _json(ITEM)},
            }
        },
    },
}


def test_parse_operations():
    ops = {o.operation_id: o for o in api_gen.parse_operations(SPEC)}
    get = ops["getItem"]
    assert (get.func_name, get.method, get.status_code, get.response_type) == (
        "get_item",
        "get",
        200,
        "schemas.Item",
    )
    assert get.signature == [
        "item_id: Annotated[int, Path()]",
        "handlers: Annotated[ApiHandlers, Depends(get_handlers)]",
        "limit: Annotated[int, Query(ge=1)] = 20",
        "q: Annotated[str | None, Query()] = None",
    ]
    assert get.call_args == "item_id=item_id, limit=limit, q=q"
    assert ops["deleteItem"].status_code == 204 and ops["deleteItem"].response_type is None
    create = ops["createItem"]
    assert create.status_code == 201
    assert create.signature[0] == "body: Annotated[schemas.ItemCreate, Body()]"


def _get_params(s):
    return s["paths"]["/items/{item_id}"]["get"]["parameters"]


def _bad_ref(s):
    schema = s["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    schema.update({"$ref": "#/components/schemas/bad_name"})


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda s: s["paths"]["/items"]["post"].pop("operationId"), "operationId"),
        (lambda s: s["paths"]["/items/{item_id}"]["delete"]["parameters"].clear(), "item_id"),
        (_bad_ref, "PascalCase"),
        (lambda s: _get_params(s)[2].update(name="qQ"), "snake_case"),
        (lambda s: s["paths"]["/items"]["post"].update(responses={"400": {}}), "2xx"),
    ],
)
def test_parse_errors(mutate, message):
    spec = copy.deepcopy(SPEC)
    mutate(spec)
    with pytest.raises(CodegenError, match=message):
        api_gen.parse_operations(spec)
