# 🍬 OITELU (オイテル) システム

**〜 NFCカードで「お菓子」を管理するスマートIoTシステム 〜**

OITELUは、Raspberry PiとNFC技術を活用した、お菓子の在庫管理・提供システムです。
社員証や学生証などのICカードをかざすだけで、自動でお菓子を取り出したり、利用履歴を記録したりすることができます。

---

## ✨ 主な特徴

- **簡単操作**: ICカードをかざすだけのシンプル操作
- **自動登録モード** ⭐ **NEW**: 未登録カードも自動で登録して利用可能！
- **Web管理**: ブラウザから在庫状況や利用履歴をリアルタイムで確認
- **どこでも接続**: Tailscale VPNを利用し、離れた場所にある登録機も安全に接続
- **Docker対応**: コマンド一つでサーバーが立ち上がります
- **複数登録機対応**: 親機と従親機が同じMySQLデータベースを共有

---

## � シンプルなファイル構成

チームメンバーが混乱しないよう、**主要ファイルは3つ**に整理しました。

```
📦 oiteru_250827_restAPI/
├── 🖥️ server.py       ← 親機 / 従親機（Webサーバー）
├── �️ db_server.py    ← 親機DB版（MySQL + Webサーバー一体型）
├── 📡 unit.py          ← 子機（NFC読み取り + モーター制御）
│
├── 📄 db_adapter.py    ← データベース抽象化（SQLite/MySQL両対応）
├── 📄 unit_client.py   ← 子機の詳細実装（unit.pyから呼び出し）
├── 📄 config.json      ← 子機の設定ファイル
├── 📄 .env.example     ← サーバーの設定ファイル（テンプレート）
│
├── 🐳 docker-compose.mysql.yml      ← 親機DB版用
├── 🐳 docker-compose.external-db.yml ← 従親機用
│
├── 📁 templates/       ← Web画面テンプレート
├── 📁 static/          ← CSS/画像
├── 📁 scripts/         ← 便利スクリプト
└── � 取説書/          ← このドキュメント
```

### 使用するファイルの選び方

| あなたの役割 | 使用するファイル | 説明 |
|:---|:---|:---|
| **親機（DB持ち）を起動したい** | `db_server.py` | MySQLデータベースを含むメインサーバー |
| **従親機を起動したい** | `server.py` | 親機のDBに接続するサブサーバー |
| **子機を起動したい** | `unit.py` | Raspberry Pi用のNFC+モーター制御 |

---

## ⭐ 新機能: 自動登録モード

### 概要

**自動登録モード**を有効にすると、未登録のカードがタッチされた際に**自動的にユーザー登録**されます。

### メリット

- 🚀 **運用開始が簡単**: 事前登録作業が不要
- 👥 **公平性を確保**: 個数制限で1日あたりの取得数を制限
- 📊 **後から管理**: 管理画面で利用者の確認・編集が可能

### 設定方法

#### 方法1: 環境変数で設定（Docker/本番環境）

```bash
# .envファイルを作成
cp .env.example .env

# 編集
AUTO_REGISTER_MODE=true     # 自動登録を有効化
AUTO_REGISTER_STOCK=2       # 1日あたりの取得上限
```

#### 方法2: docker-compose.ymlで設定

```yaml
environment:
  - AUTO_REGISTER_MODE=true
  - AUTO_REGISTER_STOCK=2
```

### 動作の流れ

1. 未登録カードが子機でタッチされる
2. サーバーが自動でユーザーを登録（初期残数: 2個）
3. 即座に利用記録が行われ、お菓子が排出される
4. 管理画面に「自動登録」として履歴が残る

---

## 🏗️ システム構成図

### 用語説明

| 用語 | 説明 |
|:---|:---|
| **親機** | データベース（MySQL）を持つメインサーバー。`db_server.py` |
| **従親機** | 親機のデータベースに接続するサブサーバー。`server.py` |
| **子機** | NFCカードリーダー付きRaspberry Pi。`unit.py` |

### システム全体像

```
┌────────────────────────────────────────────┐
│              親機 (db_server.py)            │
│  ┌──────────────┐  ┌────────────────────┐  │
│  │ MySQL DB     │  │  学生証登録機能     │  │
│  │ (データベース) │  │  :5000             │  │
│  │ :3306        │  │                    │  │
│  └──────┬───────┘  └────────────────────┘  │
│         │          IP: 100.xxx.xxx.xxx     │
└─────────┼──────────────────────────────────┘
          │
          │ ← 全ての従親機・子機がここに接続
          │
    ┌─────┴─────┬─────────────────┐
    │           │                 │
    ▼           ▼                 ▼
┌────────┐  ┌────────┐      ┌────────┐
│ 従親機1 │  │ 従親機2 │      │  子機   │
│server.py│ │server.py│      │ unit.py │
│ :5000   │  │ :5000   │      │ (RPi)  │
└────────┘  └────────┘      └────────┘
```

---

## 🔰 クイックスタート

### 1. 親機（DBサーバー）を起動

```bash
# Dockerで起動（推奨）
docker-compose -f docker-compose.mysql.yml up -d

# または直接起動
python db_server.py
```

### 2. 子機を起動（Raspberry Pi）

```bash
# 自動セットアップ付きで起動
python unit.py
```

### 3. ブラウザでアクセス

- **管理画面**: http://localhost:5000
- **管理者ログイン**: http://localhost:5000/admin
  - 初期パスワード: `admin`

---

## 🔰 はじめに（初心者向けガイド）

Dockerやネットワークの専門知識がなくても大丈夫です。このガイド通りに進めれば、約30分でシステムを構築できます。

### 1. 全体の流れ

| ステップ | 内容 | 対象 |
|:---|:---|:---|
| **Step 1** | ネットワーク構築（Tailscale） | 全てのPC・Raspberry Pi |
| **Step 2** | 親機を起動（MySQL + 登録機能） | 1台のPC |
| **Step 3** | 従親機を起動（任意） | 追加のPC |
| **Step 4** | 子機を設定 | Raspberry Pi |

---

### 2. ネットワークの準備 (Tailscale)

親機・従親機・子機を安全に接続するために、無料のVPNサービス「Tailscale」を使用します。

#### 2-1. アカウント作成
1.  [Tailscale公式サイト](https://tailscale.com/) にアクセスし、「Get Started」からアカウントを作成します。

#### 2-2. 全てのマシンにTailscaleをインストール

**Windows/Mac:**
1. Tailscale アプリをインストールし、ログインします。
2. **重要**: Tailscale上のIPアドレス（例: `100.x.y.z`）をメモしてください。

**Raspberry Pi (Linux):**
```bash
# インストール
curl -fsSL https://tailscale.com/install.sh | sh

# 起動とログイン（表示されるURLにPCからアクセスして承認）
sudo tailscale up
```

---

### 3. 親機（サーバー）のセットアップ

**親機**は、MySQL データベースを持つメインサーバーです。**最初に必ず1台**立ち上げてください。

#### 3-1. 準備するもの
*   **Docker Desktop**: [公式サイト](https://www.docker.com/products/docker-desktop/)からインストール
*   このプロジェクトのファイル一式

#### 3-2. 親機の起動

```bash
# 親機を起動（MySQL + 学生証登録機能）
docker-compose -f docker-compose.multi-server.yml up -d
```

#### 3-3. 起動確認

起動したら、ブラウザで以下にアクセス：

| URL | 用途 |
|:---|:---|
| http://localhost:5000 | 学生証登録・管理画面 |
| http://localhost:8080 | phpMyAdmin（DB直接操作） |

管理画面が表示されれば成功です！🎉

#### 3-4. 従親機向けの準備（ファイアウォール設定）

従親機を追加する場合は、**親機側で** MySQLポート（3306）を開放します：

```powershell
# Windows (PowerShell管理者権限で実行)
.\scripts\open_mysql_port_windows.ps1
```

```bash
# Linux (Ubuntu/CentOS)
sudo bash scripts/open_mysql_port_linux.sh
```

#### 3-5. 親機のIPアドレスを確認

従親機から接続するために、親機のTailscale IPをメモしてください：

```bash
# TailscaleのIPを確認
tailscale ip -4
```

例: `100.114.99.67`

---

### 4. 従親機のセットアップ

**従親機**は、親機のデータベースに接続するサブサーバーです。別のPCに設置し、親機と同じ機能が使えます。

#### 4-1. 接続テスト

まず、親機のMySQLに接続できるか確認：

```powershell
# 親機のIPアドレスを指定してテスト
.\scripts\check_mysql_port.ps1 -TargetHost 100.114.99.67
```

#### 4-2. 設定ファイルを編集

`docker-compose.external-db.yml` を開き、以下を変更：

```yaml
environment:
  # ★ 親機のIPアドレスに変更（必須）
  - MYSQL_HOST=100.114.99.67
  # ★ この従親機の名前と設置場所を変更
  - SERVER_NAME=従親機(7号館)
  - SERVER_LOCATION=7号館1階
```

#### 4-3. 従親機を起動

```bash
docker-compose -f docker-compose.external-db.yml up -d
```

#### 4-4. 起動確認

ブラウザで `http://localhost:5000` を開き、親機と同じユーザーデータが表示されれば成功！

---

### 5. 子機（クライアント）のセットアップ

Raspberry Pi（子機）の設定を行います。

#### 5-1. スクリプトのダウンロード
プロジェクトフォルダをRaspberry Piにコピーします。

#### 5-2. 子機の起動（自動セットアップ）
**新機能**: 必要な環境は自動で作成されます！

```bash
# CUIモードで起動（推奨）
python unit_client.py --no-gui

# またはGUIモードで起動
python unit_client.py
```

初回起動時、以下が自動で実行されます：
- ✅ `~/.hirameki`仮想環境の作成
- ✅ 必要なライブラリの自動インストール
- ✅ sudo権限の自動取得

#### 5-3. 親機の設定
起動後、選択肢が表示されます：
```
1. そのまま起動
2. 設定メニューを開く
3. 親機を自動探知して起動
```

**推奨**: `3` を選択すると、ネットワーク上の親機/従親機を自動で見つけてくれます！

手動設定する場合は、`2`を選択してサーバーURLに親機または従親機のTailscale IPアドレスを入力：
```
サーバーURL: http://100.100.10.10:5000
子機名: unit-01
```

#### 5-4. 完全自動起動
次回以降、設定済みの状態で即座に起動するには：
```bash
python unit_client.py --no-gui --auto
```

---

## 🚀 使い方

### 基本操作

| 操作 | 手順 |
|:---|:---|
| **学生証の登録（手動）** | 親機/従親機の管理画面 → 「新規登録」 |
| **学生証の登録（自動）** | 自動登録モード有効時、カードをかざすだけで登録 |
| **利用** | 子機のNFCリーダーにカードをかざす → モーターが動作 |
| **履歴確認** | 管理画面の「利用履歴」で確認 |
| **管理者ページ** | 管理画面の「管理者ログイン」からアクセス |

### 親機・従親機での運用

- **どの登録機（親機/従親機）からでも** 学生証の登録が可能
- **登録したデータは即座に** 全ての登録機で反映
- **利用履歴も** 全登録機で共有・確認可能

---

## � API仕様

### 利用記録API

```http
POST /api/record_usage
Content-Type: application/json

{
    "card_id": "0123456789abcdef",
    "unit_name": "unit-01"
}
```

#### レスポンス（成功）

```json
{
    "success": true,
    "message": "Usage recorded",
    "user_stock": 1,
    "unit_stock": 49
}
```

#### レスポンス（自動登録が行われた場合）

履歴には「[unit-01] 自動登録 (カードID: xxx, 初期残数: 2)」と記録されます。

#### レスポンス（エラー：自動登録モードOFF時）

```json
{
    "error": "User not found",
    "auto_register": false
}
```

### 設定確認API

```http
GET /api/settings
```

```json
{
    "auto_register_mode": true,
    "auto_register_stock": 2,
    "server_name": "OITELU親機",
    "server_location": "本館1階",
    "db_type": "mysql"
}
```

---

## �🛠️ 開発者向け詳細情報

### ディレクトリ構成（シンプル版）

```
oiteru_250827_restAPI/
├── server.py           # 親機/従親機: Webサーバー ⭐ 主要ファイル
├── db_server.py        # 親機DB版: MySQL一体型 ⭐ 主要ファイル
├── unit.py             # 子機: NFC・モーター制御 ⭐ 主要ファイル
│
├── db_adapter.py       # データベース抽象化レイヤー
├── unit_client.py      # 子機の詳細実装
├── config.json         # 子機設定ファイル
├── .env.example        # サーバー設定テンプレート
│
├── docker-compose.mysql.yml      # 親機DB版用
├── docker-compose.external-db.yml # 従親機用
│
├── templates/          # Web画面テンプレート
├── static/             # CSS・画像
├── scripts/            # 便利スクリプト
└── 取説書/             # ドキュメント類
```

### docker-composeファイルの使い分け

| ファイル | 用途 | 使用場面 |
|:---|:---|:---|
| `docker-compose.mysql.yml` | **親機DB版**（MySQL + Flask） | メインサーバー |
| `docker-compose.external-db.yml` | **従親機**（外部MySQL接続） | 追加のサーバー |

### 環境変数一覧

| 変数名 | 説明 | デフォルト値 |
|:---|:---|:---|
| `DB_TYPE` | データベースの種類 | `sqlite` |
| `MYSQL_HOST` | MySQLホスト | `localhost` |
| `MYSQL_PORT` | MySQLポート | `3306` |
| `MYSQL_USER` | MySQLユーザー | `oiteru_user` |
| `MYSQL_PASSWORD` | MySQLパスワード | `oiteru_password_2025` |
| `MYSQL_DATABASE` | MySQLデータベース名 | `oiteru` |
| `AUTO_REGISTER_MODE` | 自動登録モード | `false` |
| `AUTO_REGISTER_STOCK` | 自動登録時の初期残数 | `2` |
| `SERVER_NAME` | サーバー名 | `OITERU親機` |
| `SERVER_LOCATION` | サーバー設置場所 | `未設定` |

---

## 📊 データ参照・共有

### 他のPCからデータにアクセスする方法

データベースには個人情報が含まれるため、GitHubには同期しません。以下の方法でデータにアクセスできます。

#### 方法1: 従親機を設置（推奨）

従親機を設置して、親機のデータベースに接続します。

1. 親機を起動済みの状態にする
2. 別のPCで `docker-compose.external-db.yml` を編集（親機のIPを指定）
3. 従親機を起動
4. 親機と同じデータにリアルタイムでアクセス可能

#### 方法2: データエクスポート

親機/従親機でExcel形式にエクスポートして共有します。

```bash
# 管理画面からバックアップをダウンロード
# http://localhost:5000/admin → バックアップダウンロード
```

#### 方法3: Tailscaleリモートアクセス

親機/従親機の管理画面にリモートアクセスします。

1. Tailscaleで同じアカウントにログイン
2. ブラウザで `http://100.x.x.x:5000/admin` にアクセス
3. データをリアルタイムで確認・ダウンロード

---

## ❓ トラブルシューティング

| 現象 | 確認事項 |
| :--- | :--- |
| **未登録カードでエラーになる** | `AUTO_REGISTER_MODE=true` が設定されているか確認してください。 |
| **親機に繋がらない** | Tailscaleが各マシンで「Connected」になっていますか？<br>親機のファイアウォール設定を確認してください。 |
| **従親機からDBに接続できない** | `.\scripts\check_mysql_port.ps1 -TargetHost <親機IP>` で確認<br>親機でポート3306が開いていますか？ |
| **MySQL接続エラー** | 親機側で `.\scripts\open_mysql_port_windows.ps1` を管理者権限で実行 |
| **NFCリーダーが動かない** | USBケーブルはしっかり刺さっていますか？<br>`sudo python unit.py` で実行してみてください。 |
| **Permission denied** | Raspberry PiでGPIOを操作するには権限が必要です。<br>`sudo python unit.py` で実行してみてください。 |

詳しくは [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

---

## 📚 関連ドキュメント

- [ADVANCED.md](ADVANCED.md) - **上級者向け詳細ガイド** (詳細なAPI仕様など)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング
- [CHANGELOG.md](CHANGELOG.md) - 更新履歴

---

## 📜 更新履歴

### 2025年12月22日
- ⭐ **自動登録モード**を追加
- 📁 ファイル構成をシンプル化（server.py / db_server.py / unit.py の3本柱）
- 📄 .env.example を追加

### 2025年11月28日
- 複数親機対応（従親機機能）
- データベース抽象化レイヤー（db_adapter.py）

---

## 📜 ライセンス

社内利用を想定しています。外部公開の際は担当者にご確認ください。

---

**最終更新: 2025年12月22日**

---

**最終更新: 2025年11月28日**
