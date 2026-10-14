# AI 作業ルール (このリポジトリ)

## 編集してよいもの
- 仕様: `schema/schema.yaml` (DB), `openapi/openapi.yaml` (API)
- 中身: `app/impl/` (ApiHandlers の実装), `seeds/`, `tests/impl/`, `e2e/tests/`, `docs/` (docs/er を除く), `README.md`

## 編集してはいけないもの (フックでブロックされます)
`app/generated/`, `migrations/`, `docs/er/`, `e2e/generated/`, `codegen/`, `app/core/`, `app/main.py`, `.claude/`, `.githooks/`, `.github/`, ビルド設定類。
生成物を直したくなったら **仕様を直して再生成** する。ジェネレータが仕様を表現できない場合は人間に相談する。

## 手順
1. DB 変更: `schema/schema.yaml` を編集 → `make generate` → `make migration m="内容"`
2. API 変更: `openapi/openapi.yaml` を編集 → `make generate` → 起動時/`make test` が未実装 operation を指摘するので `app/impl/handlers.py` に実装
3. 確認: `make check` → `make e2e`

## 実装ルール
- DB アクセスは `app.generated.db.models` の ORM モデル経由のみ。`text()` / `exec_driver_sql` / SQL 文字列の `execute` は禁止 (ruff TID251 とテストで検出)。
- `git commit --no-verify` 禁止。
