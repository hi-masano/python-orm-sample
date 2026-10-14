COMPOSE  := docker compose
TOOLS    := $(COMPOSE) run --rm --no-deps tools
TOOLS_DB := $(COMPOSE) run --rm tools

.PHONY: lock build test lint
lock:
	docker run --rm -v "$(CURDIR)":/w -w /w ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim uv lock
build:
	$(COMPOSE) --profile tools build
test:
	$(TOOLS) pytest -q
lint:
	$(TOOLS) ruff check .
	$(TOOLS) ruff format --check .

.PHONY: generate
generate:
	$(TOOLS) python -m codegen all
