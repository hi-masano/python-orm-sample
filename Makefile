COMPOSE  := docker compose
TOOLS    := $(COMPOSE) run --rm --no-deps tools
TOOLS_DB := $(COMPOSE) run --rm tools

.PHONY: lock build test lint up down seed
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
	npm --prefix e2e run --silent gen:types

.PHONY: migration migrate check-migrations
migration:
	@test -n "$(m)" || (echo 'usage: make migration m="message"' && exit 1)
	$(TOOLS_DB) sh -c 'alembic upgrade head && alembic revision --autogenerate -m "$(m)"'
migrate:
	$(TOOLS_DB) alembic upgrade head
check-migrations:
	$(TOOLS) python -m codegen checksum-verify
	$(TOOLS_DB) sh -c 'alembic upgrade head && alembic check'

up:
	$(COMPOSE) up -d --build --wait db api
down:
	$(COMPOSE) down -v --remove-orphans

.PHONY: seed
seed:
	$(COMPOSE) exec -T api python -m seeds.run --profile e2e

.PHONY: e2e
e2e:
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) up -d --build --wait db api
	npm --prefix e2e test

GENERATED := app/generated docs/er e2e/generated

.PHONY: check-generated check setup
check-generated: generate
	@git diff --exit-code -- $(GENERATED) \
	  || (echo "NG: 生成物が仕様と一致しません。生成物を直接編集せず、仕様を直して make generate してください" && exit 1)
	@test -z "$$(git ls-files --others --exclude-standard -- $(GENERATED))" \
	  || (echo "NG: 未追跡の生成物があります (git add してください)" && exit 1)
check: check-generated lint test check-migrations
setup:
	git config core.hooksPath .githooks
	npm --prefix e2e ci
