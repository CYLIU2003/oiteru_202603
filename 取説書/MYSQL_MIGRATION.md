# MySQL移行ガイド - OITELU親機システム

## 概要

このガイドは、OITELUシステムをSQLiteからMySQLに移行し、複数の親機PCから同じデータベースにアクセスできるようにする手順を説明します。

## 移行の目的

- **複数デバイス対応**: 複数の親機PCが同じデータベースを共有
- **スケーラビリティ**: ユーザー数・子機数の増加に対応
- **同時アクセス**: 複数の親機からの同時操作をサポート
- **データ整合性**: トランザクション処理による安全なデータ更新

## 前提条件

- Docker & Docker Compose がインストール済み
- 既存のSQLiteデータベース(`oiteru.sqlite3`)が存在する場合、バックアップを取得済み
- ネットワーク環境でMySQLサーバーにアクセス可能

## システム構成

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   親機PC 1  │     │   親機PC 2  │     │   親機PC 3  │
│   Flask App │     │   Flask App │     │   Flask App │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │   MySQL     │
                    │   Server    │
                    └─────────────┘
```

## インストール手順

### 1. ブランチの切り替え

```bash
cd /path/to/oiteru_250827_restAPI
git checkout docker_main_server_mysql
```

### 2. 必要なファイルの確認

以下のファイルが存在することを確認:

- `db_adapter.py` - データベース抽象化レイヤー
- `docker-compose.mysql.yml` - MySQL版Docker Compose設定
- `init_mysql.sql` - MySQL初期化スクリプト
- `requirements.mysql.txt` - Python依存関係(PyMySQL含む)

### 3. Dockerコンテナの起動

```bash
# MySQLコンテナとFlaskアプリを起動
docker-compose -f docker-compose.mysql.yml up -d --build
```

### 4. データベースの初期化確認

```bash
# MySQLコンテナに接続してデータベースを確認
docker exec -it oiteru_mysql mysql -u oiteru_user -p
# パスワード: oiteru_password_2025

# MySQL内で実行
USE oiteru;
SHOW TABLES;
SELECT * FROM info;  # 管理者パスワードの確認
```

### 5. Flaskアプリケーションのログ確認

```bash
docker logs -f oiteru_flask
```

正常に起動すると、以下のようなメッセージが表示されます:

```
データベース接続: MySQL (mysql:3306/oiteru)
============================================================
OITELU親機を起動しています...
============================================================
システム診断を実行中...
✓ Python version: 3.10.x
✓ Database connection: OK (MySQL)
...
```

## 既存データの移行

SQLiteから既存データを移行する場合:

### オプション1: 管理画面からExcelエクスポート/インポート

1. **旧システム(SQLite)でデータをエクスポート**
   - ブラウザで `http://localhost:5000/admin/login` にアクセス
   - 管理者ダッシュボード → データバックアップ → Excel形式でダウンロード

2. **新システム(MySQL)でデータをインポート**
   - 新しいMySQLシステムで管理画面にログイン
   - データ復元 → Excelファイルをアップロード

### オプション2: SQLiteからMySQLに直接変換(手動)

```bash
# SQLiteデータをCSVにエクスポート
sqlite3 oiteru.sqlite3 <<EOF
.headers on
.mode csv
.output users.csv
SELECT * FROM users;
.output units.csv
SELECT * FROM units;
.output history.csv
SELECT * FROM history;
EOF

# MySQLにインポート
docker exec -i oiteru_mysql mysql -u oiteru_user -poiteru_password_2025 oiteru <<EOF
LOAD DATA LOCAL INFILE '/path/to/users.csv' 
INTO TABLE users 
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;
EOF
```

## 環境変数の設定

Flaskアプリケーションで以下の環境変数を設定:

```bash
# MySQLモード
export DB_TYPE=mysql
export MYSQL_HOST=mysql        # or IPアドレス
export MYSQL_PORT=3306
export MYSQL_DATABASE=oiteru
export MYSQL_USER=oiteru_user
export MYSQL_PASSWORD=oiteru_password_2025

# SQLiteモード(デフォルト)
export DB_TYPE=sqlite
# MYSQL_*変数は不要
```

## 複数親機PCの設定

### 親機PC #1 (MySQLサーバー付き)

```yaml
# docker-compose.mysql.ymlをそのまま使用
services:
  mysql:
    ...
  flask:
    environment:
      - MYSQL_HOST=mysql  # ローカルMySQLコンテナ
```

### 親機PC #2, #3 (MySQLクライアントのみ)

```yaml
# docker-compose.mysql.client.ymlを使用
services:
  flask:
    environment:
      - MYSQL_HOST=192.168.1.100  # PC #1のIPアドレス
```

または、Dockerを使わずに直接実行:

```bash
export DB_TYPE=mysql
export MYSQL_HOST=192.168.1.100  # 親機PC #1のIPアドレス
export MYSQL_PORT=3306
export MYSQL_DATABASE=oiteru
export MYSQL_USER=oiteru_user
export MYSQL_PASSWORD=oiteru_password_2025

python app.py
```

## ネットワーク設定

### MySQLサーバーへの外部アクセスを許可

親機PC #1で、他のPCからMySQLにアクセスできるようにする:

```bash
# ファイアウォールでポート3306を開放(Ubuntu/Debian)
sudo ufw allow 3306/tcp

# ファイアウォールでポート3306を開放(Windows)
# PowerShellを管理者権限で実行
New-NetFirewallRule -DisplayName "MySQL" -Direction Inbound -LocalPort 3306 -Protocol TCP -Action Allow
```

### MySQLユーザー権限の確認

```sql
-- MySQLコンテナ内で実行
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'%';
FLUSH PRIVILEGES;
```

## トラブルシューティング

### MySQLに接続できない

```bash
# 接続テスト
docker exec -it oiteru_flask python3 -c "
from db_adapter import db, get_connection
print(f'DB Type: {db.db_type}')
with get_connection() as conn:
    print('Connection OK!')
"
```

### "Access denied for user" エラー

- パスワードを確認: `docker-compose.mysql.yml`の`MYSQL_PASSWORD`
- ユーザー権限を確認: `GRANT`文を実行

### "Can't connect to MySQL server" エラー

- MySQLコンテナが起動しているか確認: `docker ps`
- ネットワーク接続を確認: `docker network inspect oiteru_network`
- ファイアウォール設定を確認

### データベース初期化エラー

```bash
# MySQLコンテナを完全にリセット
docker-compose -f docker-compose.mysql.yml down -v
docker volume rm oiteru_250827_restapi_mysql_data
docker-compose -f docker-compose.mysql.yml up -d --build
```

## パフォーマンスチューニング

### MySQLの最大接続数を増やす

`docker-compose.mysql.yml`に追加:

```yaml
services:
  mysql:
    command: --max_connections=200
```

### インデックスの追加

```sql
-- よく使用されるクエリに対してインデックスを追加
CREATE INDEX idx_users_card_id ON users(card_id);
CREATE INDEX idx_units_name ON units(name);
CREATE INDEX idx_history_timestamp ON history(timestamp);
```

## セキュリティ対策

1. **パスワードの変更**
   - デフォルトパスワードを変更する
   - `docker-compose.mysql.yml`の`MYSQL_PASSWORD`を更新

2. **SSL/TLS接続**
   - 本番環境ではSSL/TLS接続を使用
   - MySQL証明書の設定が必要

3. **ファイアウォール**
   - MySQLポート(3306)を信頼できるIPアドレスのみに制限

## バックアップとリストア

### データベースバックアップ

```bash
# MySQLデータベース全体をバックアップ
docker exec oiteru_mysql mysqldump -u oiteru_user -poiteru_password_2025 oiteru > backup_$(date +%Y%m%d_%H%M%S).sql
```

### データベースリストア

```bash
# バックアップからリストア
docker exec -i oiteru_mysql mysql -u oiteru_user -poiteru_password_2025 oiteru < backup_20250101_120000.sql
```

## データベース抽象化レイヤー(`db_adapter.py`)の使い方

### 基本的な使用方法

```python
from db_adapter import db, get_connection

# データの取得
with get_connection() as conn:
    user = db.fetchone(conn, "SELECT * FROM users WHERE card_id = ?", (card_id,))
    users = db.fetchall(conn, "SELECT * FROM users")

# データの更新(自動コミット)
with get_connection() as conn:
    db.execute(conn, "UPDATE users SET stock = ? WHERE card_id = ?", (new_stock, card_id))

# with文を抜けると自動的にコミットされる
```

### プレースホルダーの自動変換

- SQLite: `?`
- MySQL: `%s`

db_adapterが自動的に変換するため、コード内では`?`を使用してください。

```python
# SQLiteでもMySQLでも動作
db.execute(conn, "INSERT INTO users (card_id, stock) VALUES (?, ?)", (card_id, stock))
```

## 関連ファイル

- `db_adapter.py` - データベース抽象化レイヤー
- `app.py` - Flaskアプリケーション(MySQL対応済み)
- `docker-compose.mysql.yml` - MySQL版Docker Compose設定
- `init_mysql.sql` - MySQL初期化スクリプト
- `requirements.mysql.txt` - Python依存関係

## 参考リンク

- [MySQL公式ドキュメント](https://dev.mysql.com/doc/)
- [PyMySQL Documentation](https://pymysql.readthedocs.io/)
- [Docker Compose ドキュメント](https://docs.docker.com/compose/)

## サポート

問題が発生した場合は、以下を確認してください:

1. Dockerログ: `docker logs oiteru_flask`, `docker logs oiteru_mysql`
2. MySQLログ: `docker exec oiteru_mysql tail -f /var/log/mysql/error.log`
3. 診断情報: ブラウザで `http://localhost:5000/admin/diagnostics` にアクセス
