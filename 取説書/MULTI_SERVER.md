# 複数親機構成ガイド

## 概要

OITERUシステムでは、複数の親機(Flaskサーバー)が1つのMySQLデータベースを共有することができます。
これにより、複数の場所に設置された親機が同じユーザーデータベースを参照し、どの親機からでも利用可能になります。

## アーキテクチャ

```
┌─────────────────┐
│  親機1号機      │ ── ポート5000
│  (メインサーバ)  │
└────────┬────────┘
         │
┌────────┴────────┐     ┌──────────────┐
│  親機2号機      │ ──  │   MySQL DB   │ ── ポート3306
│  (サブサーバ)    │     │   (共有)     │
└────────┬────────┘     └──────────────┘
         │                       │
┌────────┴────────┐             │
│  親機3号機      │ ────────────┘
│  (外部マシン)    │
└─────────────────┘
```

## 構成パターン

### パターン1: 同一マシン上で複数親機を起動

**用途**: 
- テスト環境
- 負荷分散
- ポート番号で分離

**起動方法**:
```bash
docker-compose -f docker-compose.multi-server.yml up -d
```

**アクセス先**:
- 親機1号機: http://localhost:5000
- 親機2号機: http://localhost:5001
- phpMyAdmin: http://localhost:8080

**特徴**:
- 1つのMySQLコンテナを複数のFlaskコンテナが共有
- 各親機は異なるポートで待ち受け
- Docker内部ネットワークで通信

---

### パターン2: 別マシンから外部MySQLに接続

**用途**:
- 複数の建物・フロアに親機を分散配置
- Tailscaleを使った遠隔地からの接続

**前提条件**:
1. メインサーバー(MySQL)が起動済み
2. ネットワークでポート3306が通信可能
3. メインサーバーのIPアドレスが判明

**手順**:

#### 1. メインサーバー側の準備

メインサーバーで複数親機対応の構成を起動:
```bash
docker-compose -f docker-compose.multi-server.yml up -d
```

MySQLが外部接続を許可していることを確認:
```bash
docker exec oiteru_mysql_shared mysql -u root -poiteru_root_password_2025 -e "SELECT User, Host FROM mysql.user WHERE User='oiteru_user';"
```

`Host`が`%`になっていればOK(すべてのホストからの接続を許可)

#### 2. サブサーバー側の設定

`docker-compose.external-db.yml`を編集:
```yaml
environment:
  - MYSQL_HOST=192.168.1.100  # ← メインサーバーのIPに変更
  - SERVER_NAME=親機3号機
  - SERVER_LOCATION=3階会議室
```

IPアドレスの確認方法:
```bash
# ローカルネットワークの場合
ip addr show

# Tailscaleの場合
tailscale ip -4
```

#### 3. サブサーバーを起動

```bash
docker-compose -f docker-compose.external-db.yml up -d
```

#### 4. 接続確認

```bash
# MySQLへの接続テスト
docker exec -it oiteru_flask_external mysql -h 192.168.1.100 -u oiteru_user -poiteru_password_2025 -e "SHOW DATABASES;"
```

成功すれば`oiteru`データベースが表示されます。

---

### パターン3: 既存の外部MySQLサーバーを利用

**用途**:
- 既存のMySQLサーバーを活用
- 本番環境での運用

**手順**:

#### 1. MySQLにデータベースとユーザーを作成

```sql
CREATE DATABASE oiteru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'oiteru_user'@'%' IDENTIFIED BY 'oiteru_password_2025';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'%';
FLUSH PRIVILEGES;
```

#### 2. テーブルを初期化

```bash
mysql -h <MySQLサーバーIP> -u oiteru_user -p oiteru < init_mysql.sql
```

#### 3. 環境変数を設定して親機を起動

```bash
export DB_TYPE=mysql
export MYSQL_HOST=192.168.1.100
export MYSQL_PORT=3306
export MYSQL_DATABASE=oiteru
export MYSQL_USER=oiteru_user
export MYSQL_PASSWORD=oiteru_password_2025
export SERVER_NAME="親機4号機"
export SERVER_LOCATION="4階オフィス"

python app.py
```

または`.env`ファイルを作成:
```bash
DB_TYPE=mysql
MYSQL_HOST=192.168.1.100
MYSQL_PORT=3306
MYSQL_DATABASE=oiteru
MYSQL_USER=oiteru_user
MYSQL_PASSWORD=oiteru_password_2025
SERVER_NAME=親機4号機
SERVER_LOCATION=4階オフィス
```

---

## 環境変数一覧

### データベース接続設定

| 変数名 | 説明 | デフォルト値 | 必須 |
|--------|------|--------------|------|
| `DB_TYPE` | データベースタイプ | `sqlite` | ○ |
| `MYSQL_HOST` | MySQLホスト名/IP | `mysql` | ○(MySQL使用時) |
| `MYSQL_PORT` | MySQLポート | `3306` | ○(MySQL使用時) |
| `MYSQL_DATABASE` | データベース名 | `oiteru` | ○(MySQL使用時) |
| `MYSQL_USER` | ユーザー名 | `oiteru_user` | ○(MySQL使用時) |
| `MYSQL_PASSWORD` | パスワード | - | ○(MySQL使用時) |

### サーバー識別情報 (複数親機対応)

| 変数名 | 説明 | デフォルト値 | 例 |
|--------|------|--------------|-----|
| `SERVER_NAME` | サーバー名 | `OITERU親機` | `親機1号機(メイン)` |
| `SERVER_LOCATION` | 設置場所 | `未設定` | `1階受付` |
| `HOSTNAME` | ホスト名(自動取得) | - | `oiteru-server1` |

---

## セキュリティ設定

### 1. MySQL接続を制限する

特定のIPアドレスからのみ接続を許可:

```sql
-- すべてのホストから接続可能なユーザーを削除
DROP USER 'oiteru_user'@'%';

-- 特定のIPからのみ接続を許可
CREATE USER 'oiteru_user'@'192.168.1.100' IDENTIFIED BY 'oiteru_password_2025';
CREATE USER 'oiteru_user'@'192.168.1.101' IDENTIFIED BY 'oiteru_password_2025';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'192.168.1.100';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'192.168.1.101';
FLUSH PRIVILEGES;
```

### 2. ファイアウォール設定

MySQLポート(3306)を特定のIPからのみ許可:

```bash
# Ubuntu/Debian
sudo ufw allow from 192.168.1.100 to any port 3306
sudo ufw allow from 192.168.1.101 to any port 3306

# CentOS/RHEL
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.100" port protocol="tcp" port="3306" accept'
sudo firewall-cmd --reload
```

### 3. パスワードの変更

デフォルトパスワードは必ず変更してください:

```sql
ALTER USER 'oiteru_user'@'%' IDENTIFIED BY '新しい強固なパスワード';
ALTER USER 'root'@'%' IDENTIFIED BY '新しいrootパスワード';
FLUSH PRIVILEGES;
```

---

## トラブルシューティング

### 問題1: 外部から接続できない

**原因**: ファイアウォールまたはbind-address設定

**確認方法**:
```bash
# MySQLの設定確認
docker exec oiteru_mysql_shared mysql -u root -p -e "SHOW VARIABLES LIKE 'bind_address';"
```

`bind_address`が`0.0.0.0`または`::`になっているか確認。

**解決方法**:
```bash
# docker-compose.multi-server.ymlに以下が含まれているか確認
command:
  - --bind-address=0.0.0.0
```

### 問題2: 接続は成功するがデータが見えない

**原因**: データベース名が間違っている

**確認方法**:
```bash
docker exec -it oiteru_flask_server2 env | grep MYSQL
```

**解決方法**:
環境変数`MYSQL_DATABASE`が正しいか確認。

### 問題3: 同時接続数エラー

**原因**: MySQL最大接続数の制限

**確認方法**:
```bash
docker exec oiteru_mysql_shared mysql -u root -p -e "SHOW VARIABLES LIKE 'max_connections';"
```

**解決方法**:
`docker-compose.multi-server.yml`の`max-connections`を増やす:
```yaml
command:
  - --max-connections=500
```

### 問題4: 親機の識別ができない

**原因**: 環境変数が設定されていない

**確認方法**:
管理画面でサーバー情報が「未設定」になっている。

**解決方法**:
Docker起動時に環境変数を指定:
```yaml
environment:
  - SERVER_NAME=親機A
  - SERVER_LOCATION=1階ロビー
```

---

## データバックアップ

複数親機構成では、どの親機からでもバックアップ可能です。

### 方法1: Web管理画面から

1. 任意の親機の管理画面にアクセス
2. 「データバックアップ」ボタンをクリック
3. Excelファイルがダウンロードされる

### 方法2: phpMyAdmin から

1. http://localhost:8080 にアクセス
2. `oiteru`データベースを選択
3. 「エクスポート」タブでSQL形式でダウンロード

### 方法3: コマンドラインから

```bash
# 全データベースのバックアップ
docker exec oiteru_mysql_shared mysqldump -u root -poiteru_root_password_2025 --all-databases > backup_all.sql

# oiteru データベースのみバックアップ
docker exec oiteru_mysql_shared mysqldump -u root -poiteru_root_password_2025 oiteru > backup_oiteru.sql
```

### 復元方法

```bash
docker exec -i oiteru_mysql_shared mysql -u root -poiteru_root_password_2025 oiteru < backup_oiteru.sql
```

---

## モニタリング

### 接続中の親機を確認

```sql
SELECT 
  ID, 
  USER, 
  HOST, 
  DB, 
  COMMAND, 
  TIME, 
  STATE 
FROM information_schema.PROCESSLIST 
WHERE DB = 'oiteru';
```

### 各親機の状態確認

管理画面の「子機一覧」から、どの子機がどの親機に接続しているか確認できます。

---

## まとめ

| 構成 | メリット | デメリット | 推奨用途 |
|------|----------|------------|----------|
| 同一マシン複数親機 | 設定が簡単 | 1台障害で全停止 | テスト環境 |
| 別マシン外部接続 | 冗長性が高い | ネットワーク設定が必要 | 本番環境 |
| 既存MySQL利用 | インフラ共有 | 既存システムへの影響 | 既存環境への追加 |

複数親機構成により、以下が実現できます:
- ✅ ユーザーデータの一元管理
- ✅ どの親機からでも同じユーザーが利用可能
- ✅ 負荷分散とバックアップ
- ✅ 複数拠点での展開

---

## 参考リンク

- [MySQL公式ドキュメント](https://dev.mysql.com/doc/)
- [Docker Compose リファレンス](https://docs.docker.com/compose/)
- [Tailscale VPN](https://tailscale.com/)
