# python-orm-sample

仕様駆動 (Spec-Driven) で作る FastAPI + PostgreSQL + SQLAlchemy 2.0 のサンプルです。
**DB スキーマ (`schema/schema.yaml`) と API 仕様 (`openapi/openapi.yaml`) だけを人間/AI が書き、ORM モデル・DTO・ルータ・マイグレーション・ER 図・E2E 用の型は機械生成**します。
AI (Claude Code) が編集してよい範囲を「仕様」と「中身」に絞り、生成物の手編集や生 SQL を多層のガードレールで防ぎます。

## 目次

1. [このリポジトリについて](#1-このリポジトリについて)
2. [スキーマの編集方法](#2-スキーマの編集方法)
3. [ORM の操作方法](#3-orm-の操作方法)
4. [API エンドポイントの編集方法](#4-api-エンドポイントの編集方法)
5. [codegen](#5-codegen)
6. [テストの実行方法](#6-テストの実行方法)
7. [ガードレール](#7-ガードレール)

## 1. このリポジトリについて

### 目的

- 「仕様を直す → 再生成 → 中身を実装する」という一方向の流れを強制し、仕様と実装のズレをなくす。
- ORM (SQLAlchemy) だけで DB を扱う実装例を示す (生 SQL は禁止)。
- AI に任せる範囲を allowlist で明示し、触ってはいけないものを機械的にブロックする。

### 構成 (SoT → 生成物の流れ)

```text
schema/schema.yaml  (DB の SoT)
   │  python -m codegen models / er
   ├─▶ app/generated/db/models.py   SQLAlchemy ORM モデル (自作 Jinja テンプレート)
   ├─▶ docs/er/schema.md            ER 図 (Mermaid)
   │
   │  alembic revision --autogenerate (models.py と DB の差分)
   └─▶ migrations/versions/*.py     マイグレーション
         └─ post_write_hooks: ruff format → チェックサム登録 → ER 図再生成

openapi/openapi.yaml  (API の SoT)
   │  python -m codegen api
   ├─▶ app/generated/api/schemas.py   Pydantic DTO (datamodel-code-generator)
   ├─▶ app/generated/api/handlers.py  ApiHandlers 抽象クラス (自作 Jinja テンプレート)
   ├─▶ app/generated/api/routers.py   FastAPI ルータ (自作 Jinja テンプレート)
   │
   │  openapi-typescript (make generate 内で実行)
   └─▶ e2e/generated/api.d.ts         Playwright 用の型

app/impl/handlers.py  ← ApiHandlers を継承して実装する (ORM 経由で DB アクセス)
app/main.py           ← 生成ルータ + Handlers を配線するだけ
```

### ディレクトリと編集者

| パス | 役割 | 誰が編集するか |
| --- | --- | --- |
| `schema/schema.yaml` | DB スキーマの SoT | AI 可 / 人間 |
| `openapi/openapi.yaml` | API 仕様の SoT | AI 可 / 人間 |
| `app/impl/` | `ApiHandlers` の実装 (ORM 操作) | AI 可 / 人間 |
| `seeds/` | ORM オブジェクトによるシードデータ | AI 可 / 人間 |
| `tests/impl/`, `e2e/tests/` | 実装側のテスト、Playwright E2E テスト | AI 可 / 人間 |
| `docs/` (`docs/er/` を除く), `README.md` | ドキュメント | AI 可 / 人間 |
| `app/generated/` | ORM モデル・DTO・ルータ・抽象ハンドラ | 生成物 (編集禁止) |
| `migrations/` | Alembic マイグレーションと `checksums.txt` | 生成物 (編集禁止) |
| `docs/er/` | ER 図 | 生成物 (編集禁止) |
| `e2e/generated/` | OpenAPI から生成した TypeScript 型 | 生成物 (編集禁止) |
| `codegen/` | ジェネレータ本体とテンプレート | 人間のみ |
| `app/core/`, `app/main.py` | 設定・DB セッション・配線 | 人間のみ |
| `.claude/`, `.githooks/`, `.github/`, `CLAUDE.md` | ガードレール・AI 作業ルール | 人間のみ |
| `Makefile`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, `alembic.ini` | ビルド・設定類 | 人間のみ |
| `tests/` (`tests/impl/` を除く) | codegen 単体テスト・契約テスト・ガードフックテスト等 | 人間のみ |

AI が書いてよい範囲の正は `.claude/hooks/guard.py` の allowlist と `CLAUDE.md` です。

### ER 図

[docs/er/schema.md](docs/er/schema.md) (Mermaid。GitHub 上でそのまま描画されます)。`schema/schema.yaml` から自動生成されます。

### コマンド一覧 (Makefile)

Python 系のコマンドはすべて Docker Compose の `tools` コンテナ内で実行されます。ホストに必要なのは Docker と Node.js (E2E 用) だけです。

| コマンド | 内容 |
| --- | --- |
| `make setup` | `core.hooksPath` を `.githooks` に設定し、`e2e/` の npm 依存をインストール (初回に 1 回) |
| `make build` | `tools` / `api` イメージをビルド |
| `make lock` | `uv lock` で `uv.lock` を更新 |
| `make generate` | 全生成 (`python -m codegen all`) + `e2e/generated/api.d.ts` |
| `make migration m="説明"` | DB を最新化してから `alembic revision --autogenerate` |
| `make migrate` | `alembic upgrade head` |
| `make check-migrations` | マイグレーションのチェックサム検証 + `alembic upgrade head` + `alembic check` |
| `make check-generated` | 再生成して `app/generated docs/er e2e/generated` に差分/未追跡ファイルがないか検査 |
| `make up` / `make down` | `db` + `api` を起動 / 停止 (ボリュームも削除) |
| `make seed` | 起動中の `api` コンテナで seeder (profile `e2e`) を実行 |
| `make test` | `pytest -q` |
| `make lint` | `ruff check .` と `ruff format --check .` |
| `make check` | `check-generated` + `lint` + `test` + `check-migrations` |
| `make e2e` | compose を作り直して `db` + `api` を起動し、Playwright を実行 |

初回は `make setup && make build` を実行してください。

## 2. スキーマの編集方法

DB スキーマは `schema/schema.yaml` だけを編集します。書式の検証は `codegen/schema_spec.json` (JSON Schema) で行われ、未知のキーはエラーになります。

### 書式

```yaml
tables:
  posts:                       # テーブル名 (snake_case)
    model: Post                # ORM クラス名 (PascalCase)。association: true のときは省略
    comment: 投稿              # テーブルコメント (任意)
    columns:
      id: {type: integer, primary_key: true}
      author_id: {type: integer, foreign_key: users.id, on_delete: CASCADE, index: true}
      title: {type: string, length: 200}
      published: {type: boolean, server_default: "false"}
    relationships:
      author: {target: users, back_populates: posts}
      tags: {target: tags, many: true, secondary: post_tags, back_populates: posts}
```

テーブル直下のキー:

| キー | 内容 |
| --- | --- |
| `model` | ORM クラス名 (PascalCase) |
| `association` | `true` にすると ORM クラスを作らない中間テーブル (`Table` として生成) |
| `comment` | テーブルコメント |
| `columns` | カラム定義 (必須) |
| `relationships` | リレーション定義 (任意) |

`columns` の各キー:

| キー | 値 | 備考 |
| --- | --- | --- |
| `type` (必須) | `integer` / `bigint` / `string` / `text` / `boolean` / `datetime` | `datetime` は `DateTime(timezone=True)` |
| `length` | 整数 | `string` の長さ。**`type: string` では必須** (省略すると `CodegenError`) |
| `primary_key` | bool | 複合主キーは複数カラムに指定 |
| `nullable` | bool | 省略時は `NOT NULL` (`nullable=False`) |
| `unique` | bool | |
| `index` | bool | |
| `foreign_key` | `テーブル.カラム` | 例: `users.id` |
| `on_delete` | `CASCADE` / `SET NULL` / `RESTRICT` | `foreign_key` と併用 |
| `server_default` | `now` / `true` / `false` | `now` は `func.now()`。YAML では `"true"` / `"false"` のように必ず引用符付きの文字列で書く (引用符なしは YAML の真偽値になり enum 検証で失敗する) |
| `comment` | 文字列 | カラムコメント |

`relationships` の各キー:

| キー | 内容 |
| --- | --- |
| `target` (必須) | 相手のテーブル名 (モデル名ではなく `schema.yaml` のテーブル名) |
| `many` | `true` なら `Mapped[list[...]]` (1 対多/多対多の「多」側) |
| `secondary` | 多対多の中間テーブル名 (`association: true` のテーブル) |
| `back_populates` | 相手側のリレーション名 |

### DB関連手順

1. `schema/schema.yaml` を編集する。
2. `make generate` で `app/generated/db/models.py` と `docs/er/schema.md` を再生成する。
3. `make migration m="変更内容"` でマイグレーションを生成する (DB を最新化してから `--autogenerate`。生成直後にフックが整形・チェックサム登録・ER 図再生成を行う)。
4. `make check-migrations` で検証する。

### 具体例: users に bio カラムを追加する

```yaml
  users:
    columns:
      # ...既存のカラム...
      bio: {type: text, nullable: true, comment: 自己紹介}
```

```bash
make generate
make migration m="add bio to users"
make check-migrations
```

- `models.py` の `User` に `bio: Mapped[str | None]` が増えます (`nullable: true` のため。実際の出力は `app/generated/db/models.py` で確認してください)。
- `migrations/versions/` に `add_bio_to_users` のマイグレーションと `migrations/checksums.txt` の追記、`docs/er/schema.md` の更新が入ります。
- API のレスポンスには自動では出ません。返したい場合は `openapi/openapi.yaml` の `User` に `bio` を足し ([4 章](#4-api-エンドポイントの編集方法))、必要なら `make generate` 後に実装を調整します。

### マイグレーションファイルは手編集禁止

生成直後の `migrations/versions/*.py` は SHA-256 が `migrations/checksums.txt` に登録されます。後から 1 文字でも変えると `make check-migrations` (`python -m codegen checksum-verify`) が「生成後に改変されています」で失敗します。`alembic revision` 以外で作ったファイル (未登録) や、ファイルを消した場合 (マニフェストだけ残る) も検出します。直したいときはスキーマを直して新しいマイグレーションを作ってください。

## 3. ORM の操作方法

DB アクセスは `app.generated.db.models` の ORM モデル経由のみです。

### Session が Handlers に渡る仕組み

`app/main.py` の `get_handlers` が FastAPI の依存性注入で `Session` を受け取り、`Handlers` を作ります。生成ルータは `Depends(get_handlers)` でこれを呼びます。

```python
# app/main.py
def get_handlers(session: Annotated[Session, Depends(get_session)]) -> Handlers:
    return Handlers(session)
```

`get_session` は `app/core/db.py` にあり、リクエストごとに `SessionLocal()` を開いて閉じます (`autoflush=False`, `expire_on_commit=False`)。`Handlers` は `__init__` で `self.session` として保持します。

```python
# app/impl/handlers.py
class Handlers(ApiHandlers):
    def __init__(self, session: Session) -> None:
        self.session = session
```

### 基本操作 (すべて `app/impl/handlers.py` の抜粋)

SELECT (`select` + `order_by` / `limit` / `offset`):

```python
stmt = select(models.User).order_by(models.User.id).limit(limit).offset(offset)
rows = self.session.scalars(stmt)
```

条件付き 1 件取得 (`session.scalar` + `where`):

```python
exists = self.session.scalar(select(models.User).where(models.User.email == body.email))
```

主キー取得 (`session.get`):

```python
user = self.session.get(models.User, user_id)
if user is None:
    raise HTTPException(status_code=404, detail="user not found")
```

INSERT (`add` → `commit` → `refresh`)。DB 側のデフォルト (`id`, `created_at`) は `refresh` で取り込みます:

```python
user = models.User(email=body.email, name=body.name)
self.session.add(user)
self.session.commit()
self.session.refresh(user)
```

DELETE (`session.delete` → `commit`)。`posts` → `post_tags` は FK の `ON DELETE CASCADE` で消えます:

```python
self.session.delete(self._post_or_404(post_id))
self.session.commit()
```

### relationship / selectinload / `.any()`

`Post.tags` は多対多の relationship です。一覧で N+1 を避けるため `selectinload` で先読みし、タグ名での絞り込みは `.any()` で書きます (JOIN を手書きしない)。

```python
stmt = select(models.Post).options(selectinload(models.Post.tags)).order_by(models.Post.id)
if tag is not None:
    stmt = stmt.where(models.Post.tags.any(models.Tag.name == tag))
if author_id is not None:
    stmt = stmt.where(models.Post.author_id == author_id)
```

作成時は relationship に ORM オブジェクトのリストを渡すだけで中間テーブルに行が入ります。

```python
post = models.Post(author_id=body.author_id, title=body.title, body=body.body,
                   published=body.published, tags=tags)
```

### Pydantic DTO への変換

ORM オブジェクトはそのまま返さず、生成された DTO に `model_validate(obj, from_attributes=True)` で変換します。

```python
return [schemas.User.model_validate(u, from_attributes=True) for u in rows]
```

### seeder (`seeds/`)

seeder も ORM オブジェクトを `add_all` するだけで、生成モデルを使うのでスキーマ変更時に型/属性エラーで気付けます。

```python
# seeds/e2e.py
alice = User(email="alice@example.com", name="Alice")
alice.posts = [Post(title="SQLAlchemy入門", body="ORM の基本", published=True, tags=[python, orm])]
```

`seeds/run.py` は全テーブルを `delete(table)` で空にしてから投入するため、何度実行しても同じ状態になります。実行は `make seed` (`python -m seeds.run --profile e2e` を `api` コンテナ内で実行) です。

profile の追加方法:

1. `seeds/` に `build() -> list[object]` を持つモジュールを作る (例: `seeds/demo.py`)。
2. `seeds/run.py` の `PROFILES` に登録する (`from seeds import demo, e2e` に直し、`PROFILES = {"e2e": e2e.build, "demo": demo.build}` とする)。
3. `python -m seeds.run --profile demo` で実行する。

### 生 SQL は禁止

理由: 型付きモデルを通すことでスキーマ変更に追従でき、SQL インジェクションの余地を作らず、実装の見通しを揃えるため。検出手段は 2 つです。

- ruff の `TID251` (banned-api): `sqlalchemy.text` (`sqlalchemy.sql.text`, `sqlalchemy.sql.expression.text` を含む) と `psycopg` の import を禁止 (`pyproject.toml`)。`make lint` で検出。
- `tests/test_no_raw_sql.py`: `app/impl/` と `seeds/` を AST で調べ、`text()` / `exec_driver_sql()` / `literal_column()` の呼び出しと `execute("SQL文字列")` を検出。`make test` で検出。

## 4. API エンドポイントの編集方法

API は `openapi/openapi.yaml` だけを編集します。

### 対応範囲と命名規則

- パラメータ名は `snake_case`、component のスキーマ名は `PascalCase`。違反は `CodegenError`。
- `operationId` は必須かつ重複不可 (これだけを検査)。camelCase は規約で、生成される関数名は snake_case に変換される (`listUsers` → `list_users`)。
- パラメータは `in: path` / `in: query` のみ、型はプリミティブ (`integer` / `number` / `string` / `boolean`)。使えるスキーマキーは `type` / `default` / `minimum` / `maximum` / `minLength` / `maxLength`。`parameters` の `$ref` は未対応。
- `requestBody` は `required: true` の `application/json` のみ。
- 2xx レスポンスは 1 operation につき 1 つ。`application/json` のみ。`204` は `content` なし。
- HTTP メソッドは `get` / `post` / `put` / `patch` / `delete`。`head` / `options` / `trace` は未対応。
- `$ref` は `#/components/schemas/` 配下のみ。
- 上記のように明示的に検査している構文 (未対応の `in` / HTTP メソッド / `$ref`、インライン object スキーマ、複数の 2xx、必須でない requestBody など) は `make generate` が `CodegenError` で失敗します。検査対象外のキー (例: `security`) は無視されるため、すべての OpenAPI 構文が検出されるわけではありません。

### API関連手順

1. `openapi/openapi.yaml` を編集する。
2. `make generate` を実行する。`app/generated/api/` の DTO・ルータ・`ApiHandlers` の抽象メソッドが更新される。
3. `ApiHandlers` に抽象メソッドが増えるので、`app/impl/handlers.py` の `Handlers` に実装する。**未実装のままだと `app/main.py` の `create_app()` が起動時に `RuntimeError` で失敗し、`tests/test_contract.py` (`test_impl_implements_every_operation`) も落ちます。**
4. `make check` → `make e2e` で確認する。必要なら `e2e/tests/` にテストを足す。

公開される `/openapi.json` は `openapi.yaml` そのものです (契約テストで保証)。

### 具体例: `GET /tags/{tag_id}` を追加する

`openapi/openapi.yaml` の `paths` に追加します。

```yaml
  /tags/{tag_id}:
    get:
      operationId: getTag
      tags: [tags]
      summary: タグ取得
      parameters:
        - {name: tag_id, in: path, required: true, schema: {type: integer}}
      responses:
        "200":
          description: OK
          content: {application/json: {schema: {$ref: "#/components/schemas/Tag"}}}
        "404":
          description: Not Found
          content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}
```

`make generate` 後、`ApiHandlers` に `get_tag` の抽象メソッドが増えるので、`app/impl/handlers.py` に実装します (引数の形は `app/generated/api/handlers.py` で確認してください)。

```python
    def get_tag(self, *, tag_id: int) -> schemas.Tag:
        tag = self.session.get(models.Tag, tag_id)
        if tag is None:
            raise HTTPException(status_code=404, detail="tag not found")
        return schemas.Tag.model_validate(tag, from_attributes=True)
```

## 5. codegen

全生成物の入口は `python -m codegen <command>` です (`make generate` は `python -m codegen all` + `openapi-typescript`)。

| サブコマンド | 内容 |
| --- | --- |
| `models` | `schema/schema.yaml` → `app/generated/db/models.py` |
| `er` | `schema/schema.yaml` → `app/generated/db/models.py` を再生成した上で `docs/er/schema.md` を生成 (`models` を内部で呼ぶ) |
| `api` | `openapi/openapi.yaml` → `app/generated/api/{schemas,handlers,routers}.py` |
| `all` | 上記すべて |
| `checksum-record <path>` | マイグレーションの SHA-256 を `migrations/checksums.txt` に登録 (`alembic.ini` の post_write_hooks から呼ばれる) |
| `checksum-verify` | `migrations/versions/*.py` が登録時から変わっていないか検証 |

### 入力 → 生成物の対応

| 入力 | 生成物 | 使うツール |
| --- | --- | --- |
| `schema/schema.yaml` | `app/generated/db/models.py` | 自作ジェネレータ + Jinja テンプレート (`codegen/templates/models.py.j2`)。入力は `codegen/schema_spec.json` で検証 |
| `app/generated/db/models.py` | `docs/er/schema.md` | 自作 (`codegen/er_gen.py`)、Mermaid `erDiagram` |
| `app/generated/db/models.py` | `migrations/versions/*.py` | Alembic autogenerate + `post_write_hooks` (`ruff format` → `checksum-record` → `codegen er`) |
| `openapi/openapi.yaml` | `app/generated/api/schemas.py` | datamodel-code-generator (pydantic v2) |
| `openapi/openapi.yaml` | `app/generated/api/handlers.py`, `routers.py` | 自作 Jinja テンプレート (`codegen/templates/handlers.py.j2`, `routers.py.j2`) |
| `openapi/openapi.yaml` | `e2e/generated/api.d.ts` | openapi-typescript (`make generate` の中で実行) |

### 決定性と DO NOT EDIT ヘッダ

- 同じ入力からは同じ出力になります (タイムスタンプなし、`ruff format` で整形、テンプレートも固定)。だから再生成して差分を取る検査が成立します。
- 生成された Python には「自動生成されています。直接編集しないでください (DO NOT EDIT)」のヘッダと入力ファイルの SHA-256 (先頭 16 文字) が入ります。`docs/er/schema.md` には DO NOT EDIT と生成元 (source) のコメント行のみで、SHA-256 は入りません。`e2e/generated/api.d.ts` は openapi-typescript 自身のヘッダです。

### `make check-generated` による改ざん検知

`make check-generated` は `make generate` で再生成してから、`app/generated docs/er e2e/generated` に `git diff --exit-code` と未追跡ファイルの検査を行います。

注意点 (正直な挙動):

- 検出できるのは、**ステージ済みまたはコミット済みの手編集**です。ステージしていない手編集は、再生成で上書きされて差分が出ません (元の状態に戻るだけ)。
- 逆に、仕様を変えて再生成した生成物をステージし忘れると差分として検出されます。仕様の変更と生成物は同じコミットに入れてください。
- 新規の生成物 (未追跡) は「`git add` してください」で失敗します。

## 6. テストの実行方法

| コマンド | 内容 |
| --- | --- |
| `make test` | `pytest -q`。codegen 単体 (`tests/codegen/`)、契約テスト (`tests/test_contract.py`: ルートが仕様と一致 / 全 operation 実装済み / `/openapi.json` が仕様そのもの)、ガードフック (`tests/test_guard_hook.py`)、生 SQL 検査 (`tests/test_no_raw_sql.py`)、スモークテスト |
| `make lint` | `ruff check .` と `ruff format --check .` (生 SQL 禁止の TID251 を含む) |
| `make check` | `check-generated` + `lint` + `test` + `check-migrations` (CI と同じ) |
| `make e2e` | `docker compose down -v` → `db` + `api` を起動 → `npm --prefix e2e test`。Playwright の `globalSetup` が `docker compose exec -T api python -m seeds.run --profile e2e` で seeder を実行し、`http://localhost:8000` に実際にアクセスする (`API_BASE_URL` で変更可) |

初回セットアップ:

```bash
make setup   # フック設定 + e2e の npm ci
make build   # コンテナイメージのビルド
```

個別実行の例:

```bash
# pytest (tools コンテナ経由)
docker compose run --rm --no-deps tools pytest -q -k contract
docker compose run --rm --no-deps tools pytest -q tests/test_no_raw_sql.py

# Playwright (db + api を起動済みで、特定のスペックだけ)
make up
npm --prefix e2e test -- tests/users.spec.ts
make down
```

E2E は `workers: 1` で直列に実行します (共通のシードデータを前提とするため)。

## 7. ガードレール

「AI が仕様と中身だけを触る」「生成物と仕様が一致する」ことを、層を重ねて守ります。

| 層 | 場所 | 内容 |
| --- | --- | --- |
| 1. Claude Code フック | `.claude/settings.json`, `.claude/hooks/guard.py` | Edit/Write/Bash の前に実行。書き込み先を allowlist (`schema/`, `openapi/`, `app/impl/`, `seeds/`, `tests/impl/`, `e2e/tests/`, `docs/`, `README.md` など) に限定し、`docs/er/` は除外。`--no-verify` / `core.hooksPath` を含む Bash コマンドは常に拒否。`settings.json` の `permissions.deny` も併用 |
| 2. pre-commit | `.githooks/pre-commit` (`make setup` で有効化) | コミット前に `make check-generated` → `make lint` → `checksum-verify` |
| 3. CI | `.github/workflows/ci.yml` | `make build` → `make check` → `make e2e` |

### 制約事項

- **Bash の判定はベストエフォート**です。`rm` / `mv` / `cp` / `tee` / リダイレクト / `sed -i` / `git checkout` などの「書き込みっぽい」コマンドで、保護パスに触れるものを文字列ベースで見つけているだけです。シェルの工夫 (変数展開、別言語のスクリプト経由など) で抜けられる可能性があります。
- そのため最終防衛線は pre-commit と CI です (`make check` が再生成して差分を検出し、マイグレーションはチェックサムで検出)。ただし 5 章のとおり、`check-generated` が検出できるのはステージ済み/コミット済みの手編集です。
- pre-commit は `git commit --no-verify` で回避できます。AI に対してはフックが `--no-verify` を含む Bash を拒否しますが、人間の操作までは止められません。CI が最後に同じ検査を行います。
