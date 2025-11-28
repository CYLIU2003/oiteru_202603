# OITERU システム - 上級者向けガイド

このドキュメントは、OITERUシステムの全機能、設定、運用に関する詳細情報をまとめたものです。

---

## 📚 目次

1. [複数親機構成](#1-複数親機構成)
2. [MySQL移行とデータベース管理](#2-mysql移行とデータベース管理)
3. [システム診断機能](#3-システム診断機能)
4. [リモートアクセスとデータ共有](#4-リモートアクセスとデータ共有)
5. [Docker環境での運用](#5-docker環境での運用)
6. [NFCカードリーダーの設定](#6-nfcカードリーダーの設定)
7. [センサー機能とハードウェア制御](#7-センサー機能とハードウェア制御)
8. [API仕様](#8-api仕様)
9. [開発・カスタマイズ](#9-開発カスタマイズ)

---

## 1. 複数親機構成

### 概要
複数の親機(Flaskサーバー)が1つのMySQLデータベースを共有し、どの親機からでも同じユーザーデータにアクセスできます。

### アーキテクチャ
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

### セットアップ方法

#### パターンA: 同一マシン上で複数親機

**使用ファイル:** `docker-compose.multi-server.yml`

```bash
# 対話型セットアップ(推奨)
./scripts/setup_multi_server.sh

# または直接起動
docker-compose -f docker-compose.multi-server.yml up -d
```

**アクセス先:**
- 親機1号機: http://localhost:5000
- 親機2号機: http://localhost:5001
- phpMyAdmin: http://localhost:8080

**設定のカスタマイズ:**
```yaml
environment:
  - SERVER_NAME=親機1号機(メイン)    # サーバー名
  - SERVER_LOCATION=1階受付           # 設置場所
```

#### パターンB: 別マシンから外部MySQLに接続

**1. メインサーバー側:**
```bash
docker-compose -f docker-compose.multi-server.yml up -d
```

**2. サブサーバー側:**

`docker-compose.external-db.yml`を編集:
```yaml
environment:
  - MYSQL_HOST=192.168.1.100  # メインサーバーのIPに変更
  - MYSQL_PORT=3306
  - SERVER_NAME=親機3号機
  - SERVER_LOCATION=3階会議室
```

起動:
```bash
docker-compose -f docker-compose.external-db.yml up -d
```

**3. 接続確認:**
```bash
# MySQLへの接続テスト
docker exec -it oiteru_flask_external mysql \
  -h 192.168.1.100 \
  -u oiteru_user \
  -poiteru_password_2025 \
  -e "SHOW DATABASES;"
```

#### パターンC: 既存のMySQLサーバーを利用

**1. MySQLにデータベース作成:**
```sql
CREATE DATABASE oiteru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'oiteru_user'@'%' IDENTIFIED BY 'oiteru_password_2025';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'%';
FLUSH PRIVILEGES;
```

**2. テーブル初期化:**
```bash
mysql -h <MySQLサーバーIP> -u oiteru_user -p oiteru < init_mysql.sql
```

**3. 環境変数設定:**
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

### セキュリティ設定

#### MySQL接続を制限
```sql
-- 特定のIPからのみ接続を許可
DROP USER 'oiteru_user'@'%';
CREATE USER 'oiteru_user'@'192.168.1.100' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'192.168.1.100';
FLUSH PRIVILEGES;
```

#### ファイアウォール設定
```bash
# Ubuntu/Debian
sudo ufw allow from 192.168.1.100 to any port 3306

# CentOS/RHEL
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.100" port protocol="tcp" port="3306" accept'
sudo firewall-cmd --reload
```

---

## 2. MySQL移行とデータベース管理

### SQLiteからMySQLへの移行

#### 手順

**1. 既存データのバックアップ:**
```bash
# 管理画面から「データバックアップ」をクリック
# または
python data_viewer.py export-all
```

**2. MySQL環境の起動:**
```bash
docker-compose -f docker-compose.mysql.yml up -d
```

**3. データの復元:**
```bash
# 管理画面の「データ復元」からExcelファイルをアップロード
```

### データベース管理

#### phpMyAdminでの管理
```bash
# phpMyAdminを含む構成で起動
docker-compose -f docker-compose.multi-server.yml up -d

# アクセス
# http://localhost:8080
# ユーザー名: oiteru_user
# パスワード: oiteru_password_2025
```

#### コマンドラインでの管理

**バックアップ:**
```bash
# 全データベース
docker exec oiteru_mysql mysqldump \
  -u root -poiteru_root_password_2025 \
  --all-databases > backup_all.sql

# oiteruデータベースのみ
docker exec oiteru_mysql mysqldump \
  -u root -poiteru_root_password_2025 \
  oiteru > backup_oiteru.sql
```

**復元:**
```bash
docker exec -i oiteru_mysql mysql \
  -u root -poiteru_root_password_2025 \
  oiteru < backup_oiteru.sql
```

#### データベース構造

**テーブル一覧:**
- `users`: ユーザー情報(カードID、在庫数など)
- `units`: 子機情報(名前、パスワード、接続状態)
- `history`: 履歴ログ(type='usage'/'system'/'heartbeat')
- `info`: 管理者情報(パスワード)

**主要カラム:**
```sql
-- users テーブル
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    card_id VARCHAR(50) UNIQUE NOT NULL,
    allow TINYINT DEFAULT 1,
    entry TEXT,
    stock INT DEFAULT 2,
    today INT DEFAULT 0,
    total INT DEFAULT 0,
    last1 TEXT, last2 TEXT, ..., last10 TEXT
);

-- units テーブル
CREATE TABLE units (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    stock INT DEFAULT 0,
    connect TINYINT DEFAULT 0,
    available TINYINT DEFAULT 1,
    last_seen DATETIME,
    ip_address VARCHAR(50)
);

-- history テーブル
CREATE TABLE history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    txt TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'usage',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_type (type)
);
```

---

## 3. システム診断機能

### 起動時診断

親機・子機の起動時に自動的に以下をチェックします:

**親機診断項目:**
1. データベース接続
2. テーブル構造
3. NFCリーダー接続(ホスト側)
4. Tailscale接続
5. ネットワーク設定

**子機診断項目:**
1. Tailscale接続
2. NFCリーダー
3. GPIO/I2C
4. 親機サーバー接続
5. ネットワーク
6. 設定ファイル

### 診断結果の確認

**Web管理画面:**
```
http://localhost:5000/admin/diagnostics
```

**コマンドライン:**
```bash
# 親機診断
python diagnostics.py

# 子機診断(自動実行)
python unit_client.py
```

### 診断情報API

子機から親機に診断結果を送信:
```python
POST /api/diagnostics
{
  "unit_name": "test-01",
  "diagnostics": [
    {"component": "Tailscale", "status": "OK", "detail": "100.111.98.81"},
    {"component": "NFCリーダー", "status": "OK", "detail": "usb:054c:06c3"}
  ],
  "timestamp": "2025-11-28 12:00:00"
}
```

---

## 4. リモートアクセスとデータ共有

### Tailscale経由でのアクセス

**1. Tailscaleセットアップ:**
```bash
# 親機側
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 子機側(Raspberry Pi)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**2. IPアドレス確認:**
```bash
tailscale ip -4
# 例: 100.111.98.81
```

**3. リモートアクセス:**
```
http://100.111.98.81:5000/admin
```

### データビューアーの使用

`data_viewer.py`で外部からデータにアクセス:

**インストール:**
```bash
pip install pandas openpyxl
```

**使用方法:**
```bash
# 全データをExcel出力
python data_viewer.py export-all

# ユーザー一覧を表示
python data_viewer.py list-users

# 子機一覧を表示
python data_viewer.py list-units

# 利用履歴を表示(最新100件)
python data_viewer.py show-history --limit 100
```

**出力ファイル:**
- `oiteru_export_all_YYYYMMDD_HHMMSS.xlsx`

---

## 5. Docker環境での運用

### Docker Compose設定ファイル

| ファイル名 | 用途 |
|-----------|------|
| `docker-compose.yml` | SQLite版(開発用) |
| `docker-compose.mysql.yml` | MySQL版(単一親機) |
| `docker-compose.multi-server.yml` | 複数親機構成 |
| `docker-compose.external-db.yml` | 外部MySQL接続 |
| `docker-compose.unit.yml` | 子機Docker版 |

### 基本コマンド

```bash
# 起動
docker-compose -f docker-compose.mysql.yml up -d

# 停止
docker-compose -f docker-compose.mysql.yml down

# ログ確認
docker-compose -f docker-compose.mysql.yml logs -f

# 再起動
docker-compose -f docker-compose.mysql.yml restart

# コンテナに入る
docker exec -it oiteru_flask bash
docker exec -it oiteru_mysql bash
```

### ボリューム管理

**データ永続化:**
```bash
# ボリューム一覧
docker volume ls

# MySQLデータのバックアップ
docker run --rm \
  -v oiteru_mysql_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/mysql_backup.tar.gz -C /data .

# 復元
docker run --rm \
  -v oiteru_mysql_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/mysql_backup.tar.gz -C /data
```

### NFCリーダーのUSB接続(WSL2)

**Windows側でusbipd-winを使用:**
```powershell
# 管理者権限でPowerShell実行
usbipd list
usbipd bind --busid 1-4
usbipd attach --wsl --busid 1-4
```

**自動接続スクリプト:**
```bash
# scripts/auto_attach_card_reader.sh を実行
./scripts/auto_attach_card_reader.sh
```

---

## 6. NFCカードリーダーの設定

### 対応リーダー
- Sony PaSoRi RC-S380 (推奨)
- Sony PaSoRi RC-S370
- Sony PaSoRi RC-S330
- その他FeliCa対応リーダー

### ドライバーインストール

**Raspberry Pi:**
```bash
sudo apt-get update
sudo apt-get install -y pcscd libpcsclite-dev libusb-1.0-0-dev
sudo systemctl start pcscd
sudo systemctl enable pcscd
```

**Python nfcpyインストール:**
```bash
pip install nfcpy
```

### 動作確認

```bash
# リーダー検出
python -c "import nfc; print(nfc.ContactlessFrontend('usb'))"

# カード読み取りテスト
python -c "
import nfc
clf = nfc.ContactlessFrontend('usb')
tag = clf.connect(rdwr={'on-connect': lambda tag: True})
print('Card ID:', tag.idm.hex() if hasattr(tag, 'idm') else 'Unknown')
"
```

### トラブルシューティング

**Permission denied エラー:**
```bash
# ユーザーをdialoutグループに追加
sudo usermod -a -G dialout $USER

# udevルール作成
sudo sh -c 'echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"054c\", ATTR{idProduct}==\"06c3\", MODE=\"0666\"" > /etc/udev/rules.d/99-pcscd.rules'
sudo udevadm control --reload-rules
```

---

## 7. センサー機能とハードウェア制御

### フォトリフレクタセンサー(LBR-127HLD)

**配線:**
```
LBR-127HLD → Raspberry Pi
VCC → 3.3V or 5V
GND → GND
OUT → GPIO 22 (BCM)
```

**設定:**
```json
{
  "USE_SENSOR": true,
  "SENSOR_PIN": 22,
  "SENSOR_CHECK_PRE": true,
  "SENSOR_CHECK_POST": true,
  "JAM_CLEAR_ATTEMPTS": 3,
  "SENSOR_STABILIZE_TIME": 0.3
}
```

**テストモード:**
```bash
# スタンドアロンテスト
sudo python test_sensor.py

# unit_client統合テスト
sudo python unit_client.py --test-sensor
```

### モーター制御

**サーボモーター(PCA9685経由):**
```json
{
  "MOTOR_TYPE": "SERVO",
  "CONTROL_METHOD": "RASPI_DIRECT",
  "MOTOR_SPEED": 100,
  "MOTOR_DURATION": 2.0,
  "MOTOR_REVERSE": false
}
```

**ステッピングモーター(Arduino経由):**
```json
{
  "MOTOR_TYPE": "STEPPER",
  "CONTROL_METHOD": "ARDUINO_SERIAL",
  "ARDUINO_PORT": "/dev/ttyACM0",
  "MOTOR_SPEED": 100,
  "MOTOR_DURATION": 2.0
}
```

### LED制御

```json
{
  "GREEN_LED_PIN": 17,
  "RED_LED_PIN": 27
}
```

---

## 8. API仕様

### エンドポイント一覧

#### 子機管理

**ハートビート:**
```http
POST /api/unit/heartbeat
Content-Type: application/json

{
  "name": "test-01",
  "password": "password123",
  "ip_address": "100.111.98.81",
  "stock": 10
}

Response 200:
{
  "success": true,
  "stock": 10
}
```

**診断情報送信:**
```http
POST /api/diagnostics
Content-Type: application/json

{
  "unit_name": "test-01",
  "diagnostics": [
    {"component": "NFCリーダー", "status": "OK", "detail": "usb"}
  ],
  "timestamp": "2025-11-28 12:00:00"
}
```

**ログ送信:**
```http
POST /api/log
Content-Type: application/json

{
  "unit_name": "test-01",
  "level": "INFO",
  "message": "排出完了"
}
```

#### 利用記録

**利用記録:**
```http
POST /api/record_usage
Content-Type: application/json

{
  "card_id": "01234567890abcdef",
  "unit_name": "test-01"
}

Response 200 (成功):
{
  "success": true,
  "message": "利用を記録しました",
  "new_stock": 9
}

Response 400 (エラー):
{
  "success": false,
  "error": "未登録カード"
}
```

#### ユーザー管理

**ユーザー一覧:**
```http
GET /api/users

Response 200:
[
  {
    "id": 1,
    "card_id": "01234567890abcdef",
    "stock": 10,
    "allow": 1,
    "total": 5
  }
]
```

**ユーザー検索:**
```http
GET /api/users/<card_id>

Response 200:
{
  "id": 1,
  "card_id": "01234567890abcdef",
  "stock": 10
}
```

#### ヘルスチェック

```http
GET /api/health

Response 200:
{
  "status": "ok",
  "timestamp": "2025-11-28T12:00:00"
}
```

---

## 9. 開発・カスタマイズ

### プロジェクト構造

```
oiteru_250827_restAPI/
├── app.py                  # Flask REST APIサーバー
├── unit_client.py          # 子機クライアント
├── db_adapter.py           # データベース抽象化レイヤー
├── diagnostics.py          # システム診断
├── data_viewer.py          # データビューアー
├── test_sensor.py          # センサーテストツール
├── init_mysql.sql          # MySQLテーブル定義
├── config.json             # 子機設定ファイル
├── requirements.txt        # Python依存パッケージ(親機)
├── requirements-client.txt # Python依存パッケージ(子機)
├── docker-compose.*.yml    # Docker設定
├── Dockerfile*             # Dockerイメージ定義
├── scripts/                # 実行スクリプト集
├── templates/              # Flaskテンプレート
├── static/                 # 静的ファイル(CSS, 画像)
└── 取説書/                 # ドキュメント
```

### 環境変数

**親機:**
```bash
# データベース設定
DB_TYPE=mysql
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=oiteru
MYSQL_USER=oiteru_user
MYSQL_PASSWORD=oiteru_password_2025

# サーバー識別
SERVER_NAME=親機1号機
SERVER_LOCATION=1階受付

# その他
PCSCLITE_SOCKET=/run/pcscd/pcscd.comm
```

**子機:**
```json
{
  "SERVER_URL": "http://192.168.1.100:5000",
  "UNIT_NAME": "test-01",
  "UNIT_PASSWORD": "password123",
  "MOTOR_TYPE": "SERVO",
  "CONTROL_METHOD": "RASPI_DIRECT",
  "USE_SENSOR": true
}
```

### カスタマイズ例

#### 排出アイテム数の変更

`app.py`:
```python
# デフォルトの在庫数を変更
DEFAULT_STOCK = 5  # 10個に変更

# 1日の利用上限を変更
DAILY_LIMIT = 3  # 5回に変更
```

#### 新しいハードウェアの追加

`unit_client.py`:
```python
# 新しいセンサーを追加
def check_temperature_sensor():
    # 温度センサーの読み取り
    return sensor_value

# dispense_item()に統合
def dispense_item():
    temp = check_temperature_sensor()
    if temp > 50:
        print("警告: 高温")
    # 既存の処理...
```

### テスト

```bash
# ユニットテスト
python -m pytest tests/

# カバレッジ
python -m pytest --cov=app --cov=unit_client

# 統合テスト
docker-compose -f docker-compose.mysql.yml up -d
python tests/integration_test.py
```

### デバッグモード

```bash
# Flaskデバッグモード
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py

# 詳細ログ
python unit_client.py --verbose
```

---

## 付録: よく使うコマンド集

### 親機操作

```bash
# 起動(MySQL版)
docker-compose -f docker-compose.mysql.yml up -d

# ログ確認
docker-compose logs -f flask

# コンテナに入る
docker exec -it oiteru_flask bash

# データベース確認
docker exec -it oiteru_mysql mysql -u oiteru_user -p oiteru
```

### 子機操作

```bash
# GUIモードで起動
sudo python unit_client.py

# CUIモードで起動
sudo python unit_client.py --no-gui

# 自動探知モード
sudo python unit_client.py --find-server

# センサーテスト
sudo python unit_client.py --test-sensor
```

### メンテナンス

```bash
# データバックアップ
python data_viewer.py export-all

# MySQLバックアップ
docker exec oiteru_mysql mysqldump -u root -p oiteru > backup.sql

# ログのクリーンアップ
docker-compose logs --tail=0 > /dev/null

# 全コンテナ再起動
docker-compose down && docker-compose up -d
```

---

## サポート

問題が発生した場合:
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を確認
2. システム診断を実行: `python diagnostics.py`
3. ログを確認: `docker-compose logs`
4. GitHub Issuesで報告

---

**最終更新: 2025年11月28日**
