# OITERU | Copilot instructions

開発ルールの正本は [AGENTS.md](../AGENTS.md)、全体像は [README.md](../README.md) です。ここには要点だけを書きます。

- 親機: Flask（`server.py` / `wsgi.py` / `app/`）+ **MySQL 8 (InnoDB) のみ**。SQLite は廃止済みで、`DB_TYPE` が `mysql` 以外だと起動しません。
- 子機: Raspberry Pi 上の `unit.py`（本体は `unit/`）。NFC・GPIO・モーターはインターフェース越しに扱い、テストではモックを使います。
- 本番の親機は systemd サービス `oiteru-parent`。操作は `scripts/parent.sh status|logs|restart|install`。
- 責務分離: ルーティング `app/api/`、業務ロジック `app/services/`、DB アクセス `app/repositories/`。route や template から直接 SQL を書かないこと。
- スキーマ変更は `app/migrations.py` に migration を追加して行うこと。
- DB を使うテストは本物の MySQL で実行します（`OITERU_TEST_MYSQL=1`、DB 名は `*_test`）。
- `.env`、カード UID、パスワード、トークンをコード・ログ・資料に平文で残さないこと。
- `legacy/` は旧方式の保管場所です。新しいコードから参照しないでください。
