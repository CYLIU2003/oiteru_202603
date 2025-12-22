# 📖 OITELU リファレンスガイド（上級者向け）

このドキュメントは、OITELUシステムの**すべての機能、設定、API仕様、トラブルシューティング**を網羅したリファレンスです。

---

## 📚 目次

1. [システム構成](#1-システム構成)
2. [複数親機構成](#2-複数親機構成)
3. [データベース管理](#3-データベース管理)
4. [API仕様](#4-api仕様)
5. [設定ファイル](#5-設定ファイル)
6. [ハードウェア制御](#6-ハードウェア制御)
7. [Docker設定](#7-docker設定)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. システム構成

### 用語

| 用語 | 説明 | 起動ファイル |
|:---|:---|:---|
| **親機** | データベース（MySQL）を持つメインサーバー | `db_server.py` |
| **従親機** | 親機のデータベースに接続するサブサーバー | `server.py` |
| **子機** | NFCカードリーダー付きRaspberry Pi | `unit.py` |

### アーキテクチャ

```
┌────────────────────────────────────────────┐
│              親機 (db_server.py)            │
│  ┌──────────────┐  ┌────────────────────┐  │
│  │ MySQL DB     │  │  Webサーバー        │  │
│  │ (データベース) │  │  (:5000)           │  │
│  └──────┬───────┘  └────────────────────┘  │
└─────────┼──────────────────────────────────┘
          │
    ┌─────┴─────┬─────────────────┐
    │           │                 │
    ▼           ▼                 ▼
┌────────┐  ┌────────┐      ┌────────┐
│ 従親機  │  │ 従親機  │      │  子機   │
│server.py│ │server.py│      │ unit.py │
└────────┘  └────────┘      └────────┘
```

### ファイル構成

```
oiteru_250827_restAPI/
├── server.py          # 親機/従親機 Webサーバー
├── db_server.py       # 親機 (MySQL一体型)
├── unit.py            # 子機エントリポイント
├── db_adapter.py      # DB抽象化レイヤー
├── config.json        # 子機設定
├── .env.example       # サーバー設定テンプレート
│
├── docker/            # Docker関連
│   ├── docker-compose.mysql.yml      # 親機用
│   ├── docker-compose.external-db.yml # 従親機用
│   ├── docker-compose.multi-server.yml # 複数親機用
│   ├── Dockerfile                    # アプリイメージ
│   ├── Dockerfile.mysql              # MySQL版イメージ
│   └── init_mysql.sql                # DB初期化SQL
│
├── scripts/           # 便利スクリプト
├── tools/             # テスト・診断ツール
├── templates/         # HTML テンプレート
└── static/            # CSS, 画像
```

---

## 2. 複数親機構成

### パターンA: 同一マシン上で複数親機

```bash
cd docker
docker-compose -f docker-compose.multi-server.yml up -d
```

**アクセス先:**
- 親機1号機: http://localhost:5000
- 親機2号機: http://localhost:5001
- phpMyAdmin: http://localhost:8080

### パターンB: 別マシンから外部MySQLに接続

**1. メインサーバー側（ファイアウォール）:**

```bash
# Linux
sudo bash scripts/open_mysql_port_linux.sh

# または手動で
sudo ufw allow 3306/tcp
```

**2. クライアント側（Windows）:**

```powershell
# 管理者権限で実行
.\scripts\open_mysql_port_windows.ps1
```

**3. 接続テスト:**

```powershell
.\scripts\check_mysql_port.ps1 -TargetHost 192.168.1.100
```

**4. docker-compose.external-db.yml を編集:**

```yaml
environment:
  - MYSQL_HOST=192.168.1.100
  - MYSQL_PORT=3306
  - MYSQL_DATABASE=oiteru
  - MYSQL_USER=oiteru_user
  - MYSQL_PASSWORD=oiteru_password_2025
  - SERVER_NAME=従親機（外部）
  - SERVER_LOCATION=別棟
```

**5. 起動:**

```bash
docker-compose -f docker-compose.external-db.yml up -d
```

### パターンC: 既存のMySQLサーバーを利用

**1. データベース作成:**

```sql
CREATE DATABASE oiteru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'oiteru_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'%';
FLUSH PRIVILEGES;
```

**2. テーブル初期化:**

```bash
mysql -h <MySQLサーバーIP> -u oiteru_user -p oiteru < docker/init_mysql.sql
```

**3. 環境変数設定:**

```bash
export DB_TYPE=mysql
export MYSQL_HOST=192.168.1.100
export MYSQL_PORT=3306
export MYSQL_DATABASE=oiteru
export MYSQL_USER=oiteru_user
export MYSQL_PASSWORD=your_password

python server.py
```

### セキュリティ設定

**MySQL接続を特定IPに制限:**

```sql
DROP USER 'oiteru_user'@'%';
CREATE USER 'oiteru_user'@'192.168.1.%' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON oiteru.* TO 'oiteru_user'@'192.168.1.%';
FLUSH PRIVILEGES;
```

---

## 3. データベース管理

### テーブル構造

#### users テーブル

| カラム | 型 | 説明 |
|:---|:---|:---|
| id | INTEGER | 主キー |
| card_id | VARCHAR(100) | NFCカードID（一意） |
| allow | INTEGER | 利用許可（1=許可, 0=不許可） |
| entry | VARCHAR(50) | 登録日時 |
| stock | INTEGER | 残り利用回数 |
| today | INTEGER | 当日利用回数 |
| total | INTEGER | 累計利用回数 |

#### units テーブル

| カラム | 型 | 説明 |
|:---|:---|:---|
| id | INTEGER | 主キー |
| name | VARCHAR(100) | 子機名（一意） |
| password | VARCHAR(100) | 認証パスワード |
| stock | INTEGER | 現在の在庫数 |
| available | INTEGER | 利用可能（1=可, 0=不可） |
| connect | INTEGER | 接続状態 |
| last_seen | DATETIME | 最終接続日時 |
| ip_address | VARCHAR(45) | IPアドレス |

#### history テーブル

| カラム | 型 | 説明 |
|:---|:---|:---|
| id | INTEGER | 主キー |
| txt | TEXT | ログメッセージ |
| type | VARCHAR(20) | ログタイプ（success, system, usage） |
| created_at | DATETIME | 記録日時 |

**タイプの意味:**
- `success`: 排出成功（カードタッチ＋排出完了）
- `system`: システムログ（自動登録、在庫警告など）
- `usage`: その他の利用関連ログ

### バックアップと復元

**Excelバックアップ（管理画面）:**
1. 管理画面 → 「💾 バックアップ」
2. `.xlsx`ファイルがダウンロードされる

**コマンドラインでバックアップ（MySQL）:**

```bash
docker exec oiteru_mysql mysqldump \
  -u root -poiteru_root_password_2025 \
  oiteru > backup_$(date +%Y%m%d).sql
```

**復元:**

```bash
docker exec -i oiteru_mysql mysql \
  -u root -poiteru_root_password_2025 \
  oiteru < backup_20251222.sql
```

---

## 4. API仕様

### 認証なしAPI

#### ユーザー一覧取得

```
GET /api/users
```

**レスポンス:**
```json
[
  {
    "id": 1,
    "card_id": "01234567",
    "allow": 1,
    "entry": "2025-12-22 10:00",
    "stock": 5,
    "today": 2,
    "total": 10
  }
]
```

#### ユーザー情報取得

```
GET /api/users/<card_id>
```

### 子機用API

#### 利用記録（排出成功時に呼び出し）

```
POST /api/record_usage
Content-Type: application/json

{
  "card_id": "01234567",
  "unit_name": "子機1号機"
}
```

**成功レスポンス:**
```json
{
  "success": true,
  "message": "Usage recorded",
  "user_stock": 4,
  "unit_stock": 99
}
```

**エラーレスポンス:**
```json
{
  "error": "User not found",
  "auto_register": false
}
```

#### ハートビート（生存確認）

```
POST /api/unit/heartbeat
Content-Type: application/json

{
  "unit_name": "子機1号機",
  "password": "unit_password"
}
```

#### ログ送信

```
POST /api/log
Content-Type: application/json

{
  "message": "NFCリーダー初期化完了",
  "unit_name": "子機1号機"
}
```

### 設定同期API

#### 設定取得

```
GET /api/settings
```

**レスポンス:**
```json
{
  "auto_register_mode": true,
  "auto_register_stock": 2,
  "server_name": "親機1号機",
  "server_location": "1階受付"
}
```

---

## 5. 設定ファイル

### サーバー設定（.env）

`.env.example` をコピーして `.env` を作成:

```bash
cp .env.example .env
```

**設定項目:**

```env
# データベース設定
DB_TYPE=mysql              # mysql または sqlite
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=oiteru
MYSQL_USER=oiteru_user
MYSQL_PASSWORD=your_password

# サーバー識別
SERVER_NAME=親機1号機
SERVER_LOCATION=1階受付

# 自動登録モード
AUTO_REGISTER_MODE=true    # true: 有効, false: 無効
AUTO_REGISTER_STOCK=2      # 自動登録時の初期残数

# 管理画面
ADMIN_PASSWORD=admin       # 管理画面のパスワード

# フラスコ設定
SECRET_KEY=your-secret-key
```

### 子機設定（config.json）

```json
{
  "server_url": "http://192.168.1.100:5000",
  "unit_name": "子機1号機",
  "unit_password": "secure_password",
  
  "motor_type": "stepper",
  "control_method": "arduino",
  "arduino_port": "/dev/ttyUSB0",
  
  "use_sensor": true,
  "sensor_pin": 22,
  
  "heartbeat_interval": 30,
  "retry_interval": 5,
  "max_retries": 3
}
```

---

## 6. ハードウェア制御

### モーター制御

#### サーボモーター（PCA9685経由）

```json
{
  "motor_type": "servo",
  "control_method": "pca9685",
  "servo_channel": 15,
  "servo_open_angle": 90,
  "servo_close_angle": 0
}
```

#### ステッピングモーター（Arduino経由）

```json
{
  "motor_type": "stepper",
  "control_method": "arduino",
  "arduino_port": "/dev/ttyUSB0",
  "arduino_baud": 9600
}
```

**Arduinoスケッチ:**
→ `archive/` フォルダ内のサンプルを参照

### センサー設定

**排出検知センサー（LBR-127HLD）:**

```json
{
  "use_sensor": true,
  "sensor_pin": 22,
  "sensor_timeout": 10
}
```

**動作:**
1. モーター動作開始
2. センサーが物体通過を検知
3. 排出成功として記録

---

## 7. Docker設定

### docker-compose.mysql.yml（親機用）

```yaml
version: '3.8'
services:
  flask:
    build:
      context: ..
      dockerfile: docker/Dockerfile.mysql
    ports:
      - "5000:5000"
    environment:
      - DB_TYPE=mysql
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
    depends_on:
      - mysql

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=oiteru
    volumes:
      - mysql_data:/var/lib/mysql
```

### docker-compose.external-db.yml（従親機用）

```yaml
version: '3.8'
services:
  flask:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "5000:5000"
    environment:
      - DB_TYPE=mysql
      - MYSQL_HOST=192.168.1.100  # 親機のIP
      - MYSQL_PORT=3306
```

### よく使うコマンド

```bash
# 起動
docker-compose -f docker-compose.mysql.yml up -d

# 停止
docker-compose down

# ログ確認
docker-compose logs -f

# 再ビルド
docker-compose build --no-cache

# コンテナ内に入る
docker exec -it oiteru_flask bash
```

---

## 8. トラブルシューティング

### NFCカードリーダーの問題

#### "No such device" エラー

**原因:** USBデバイスが認識されていない

**解決方法:**
```bash
# リーダーが認識されているか確認
lsusb | grep -i sony

# udevルール設定
sudo nano /etc/udev/rules.d/99-nfc.rules
```

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="06c3", MODE="0666", GROUP="plugdev"
```

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### WSL2でUSBリーダーが認識されない

```powershell
# Windows側（管理者権限）
usbipd list
usbipd bind --busid 1-4
usbipd attach --wsl --busid 1-4
```

### サーバーの問題

#### ポートが使用中

```bash
# 使用状況確認
sudo lsof -i :5000
sudo lsof -i :3306

# プロセス停止
sudo kill -9 <PID>
```

#### MySQL接続エラー

```bash
# 接続テスト
docker exec -it oiteru_flask mysql \
  -h mysql \
  -u oiteru_user \
  -poiteru_password_2025 \
  -e "SHOW DATABASES;"

# ネットワーク確認
docker network ls
docker network inspect oiteru_network
```

### 子機の問題

#### 親機に接続できない

```bash
# ping確認
ping 親機のIP

# ポート確認
nc -zv 親機のIP 5000

# curlでAPI確認
curl http://親機のIP:5000/api/users
```

#### Permission denied

```bash
# sudoで実行
sudo python3 unit.py

# またはグループ追加
sudo usermod -a -G dialout $USER
sudo usermod -a -G plugdev $USER
# 再ログイン後に有効
```

### データベースの問題

#### テーブルが存在しない

```bash
# テーブル初期化
docker exec -i oiteru_mysql mysql \
  -u root -proot_password \
  oiteru < docker/init_mysql.sql
```

#### データ破損

```bash
# バックアップから復元
docker exec -i oiteru_mysql mysql \
  -u root -proot_password \
  oiteru < backup_YYYYMMDD.sql
```

---

## 📝 更新履歴

詳細は [CHANGELOG.md](CHANGELOG.md) を参照してください。

---

**最終更新: 2025年12月22日**
