# 🍬 OITELU (オイテル) システム

**〜 NFCカードで「お菓子」を管理するスマートIoTシステム 〜**

OITELUは、Raspberry PiとNFC技術を活用した、お菓子の在庫管理・提供システムです。
社員証や学生証などのICカードをかざすだけで、自動でお菓子を取り出したり、利用履歴を記録したりすることができます。

**新機能**: 複数の学生証登録機が同じデータベースを共有できるようになりました！

---

## 📚 目次

- [✨ 特徴](#-特徴)
- [🏗️ システム構成図](#️-システム構成図)
- [🔰 はじめに（初心者向けガイド）](#-はじめに初心者向けガイド)
    - [1. 全体の流れ](#1-全体の流れ)
    - [2. ネットワークの準備 (Tailscale)](#2-ネットワークの準備-tailscale)
    - [3. 親機（サーバー）のセットアップ](#3-親機サーバーのセットアップ)
    - [4. 従親機のセットアップ](#4-従親機のセットアップ)
    - [5. 子機（クライアント）のセットアップ](#5-子機クライアントのセットアップ)
- [🚀 使い方](#-使い方)
- [🛠️ 開発者向け詳細情報](#️-開発者向け詳細情報)
- [❓ トラブルシューティング](#-トラブルシューティング)

---

## ✨ 特徴

*   **簡単操作**: ICカードをかざすだけのシンプル操作。
*   **Web管理**: ブラウザから在庫状況や利用履歴をリアルタイムで確認。
*   **どこでも接続**: Tailscale VPNを利用し、離れた場所にある登録機も安全に接続。
*   **Docker対応**: 面倒な環境構築は不要。コマンド一つでサーバーが立ち上がります。
*   **複数登録機対応** ⭐ **NEW**: 親機と従親機が同じMySQLデータベースを共有し、どこからでも同じユーザーデータにアクセス可能。

---

## 🏗️ システム構成図

### 用語説明

| 用語 | 説明 |
|:---|:---|
| **親機** | データベース（MySQL）を持つメインサーバー。学生証登録・管理も可能 |
| **従親機** | 親機のデータベースに接続するサブサーバー。親機と同じ機能が使える |
| **子機** | NFCカードリーダー付きRaspberry Pi。カード読み取り専用 |

### システム全体像

```
┌────────────────────────────────────────────┐
│              親機 (メインサーバー)            │
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
│ (別PC)  │  │ (別PC)  │      │ (RPi)  │
│ :5000   │  │ :5000   │      │        │
└────────┘  └────────┘      └────────┘

✅ 親機・従親機で共通してできること：
   - 学生証の新規登録
   - 利用履歴の確認・エクスポート
   - 管理者ページへのアクセス
   - ユーザー情報の編集・削除
```

**メリット**:
- どの登録機で学生証を登録しても、全ての登録機で即座に使える
- 利用履歴は全登録機で共有・確認可能
- 親機がダウンしない限り、従親機でサービス継続

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
| **学生証の登録** | 親機/従親機の管理画面（`http://localhost:5000`）→「新規登録」→ ICカードをかざす |
| **利用** | 子機のNFCリーダーにカードをかざす → モーターが動作 |
| **履歴確認** | 管理画面の「利用履歴」で確認 |
| **管理者ページ** | 管理画面の「管理者ログイン」からアクセス |

### 親機・従親機での運用

- **どの登録機（親機/従親機）からでも** 学生証の登録が可能
- **登録したデータは即座に** 全ての登録機で反映
- **利用履歴も** 全登録機で共有・確認可能

---

## 🛠️ 開発者向け詳細情報

### ディレクトリ構成

```
oiteru_250827_restAPI/
├── app.py                          # 親機/従親機: Flaskサーバー本体
├── unit_client.py                  # 子機: NFC・モーター制御クライアント
├── db_adapter.py                   # データベース抽象化レイヤー
│
├── docker-compose.multi-server.yml # 親機用（MySQL + Flask）⭐ メイン
├── docker-compose.external-db.yml  # 従親機用（外部MySQL接続）⭐
├── docker-compose.mysql.yml        # シングル構成用
├── docker-compose.yml              # SQLite版（テスト用）
│
├── Dockerfile.mysql                # 親機/従親機用Dockerイメージ
├── init_mysql.sql                  # MySQLテーブル初期化スクリプト
│
├── scripts/
│   ├── open_mysql_port_windows.ps1 # Windows: ポート3306を開く
│   ├── open_mysql_port_linux.sh    # Linux: ポート3306を開く
│   └── check_mysql_port.ps1        # MySQL接続チェック
│
├── templates/                      # Web画面テンプレート
└── 取説書/                         # ドキュメント類
```

### docker-composeファイルの使い分け

| ファイル | 用途 | 使用場面 |
|:---|:---|:---|
| `docker-compose.multi-server.yml` | **親機**（MySQL + Flask） | メインサーバー |
| `docker-compose.external-db.yml` | **従親機**（外部MySQL接続） | 追加のサーバー |
| `docker-compose.mysql.yml` | シングル構成 | 1台で完結する場合 |
| `docker-compose.yml` | 開発・テスト用 | SQLite使用 |

### 新機能: データベース抽象化レイヤー

`db_adapter.py`により、SQLiteとMySQLの両方に対応しました。

**環境変数で切り替え:**
```bash
# SQLite使用（デフォルト）
export DB_TYPE=sqlite

# MySQL使用
export DB_TYPE=mysql
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_DATABASE=oiteru
export MYSQL_USER=oiteru_user
export MYSQL_PASSWORD=oiteru_password_2025
```

### Windows + WSL2 での NFCリーダー利用 (パススルー設定)

Windows上のDockerコンテナからUSBデバイス（NFCリーダー）を直接制御する場合の設定です。

#### 1. ツールインストール
*   Windows側: `winget install --id dorssel.usbipd-win`
*   WSL2側: `sudo apt install -y linux-tools-generic hwdata` 等（詳細は公式ドキュメント参照）

#### 2. デバイスのアタッチ (PowerShell管理者権限)
```powershell
# デバイス一覧確認
usbipd list

# バインド (初回のみ)
usbipd bind --busid <BUSID>

# アタッチ (毎回必要)
usbipd attach --wsl --busid <BUSID>
```

#### 3. コンテナ起動
`docker-compose.yml` には既に `privileged: true` と `/dev/bus/usb` のマウント設定が含まれています。通常通り `docker-compose up -d` で起動してください。

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

詳細は [4. 従親機のセットアップ](#4-従親機のセットアップ) を参照してください。

#### 方法2: データエクスポート

親機/従親機でExcel形式にエクスポートして共有します。

```bash
# 全データをExcel出力
python data_viewer.py export-all

# 出力されたExcelファイルをOneDrive/Google Driveで共有
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
| **親機に繋がらない** | Tailscaleが各マシンで「Connected」になっていますか？<br>親機のファイアウォール設定を確認してください。 |
| **従親機からDBに接続できない** | `.\scripts\check_mysql_port.ps1 -TargetHost <親機IP>` で確認<br>親機でポート3306が開いていますか？ |
| **MySQL接続エラー** | 親機側で `.\scripts\open_mysql_port_windows.ps1` を管理者権限で実行 |
| **NFCリーダーが動かない** | USBケーブルはしっかり刺さっていますか？<br>WSL2の場合、`usbipd attach` を忘れていませんか？ |
| **Permission denied** | Raspberry PiでGPIOを操作するには権限が必要です。<br>`sudo python unit_client.py` で実行してみてください。 |
| **データが見られない** | `data_viewer.py`を使用してExcel出力してください。 |

詳しくは [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

---

## 📚 関連ドキュメント

- [ADVANCED.md](ADVANCED.md) - **上級者向け詳細ガイド** (API仕様など)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング
- [CHANGELOG.md](CHANGELOG.md) - 更新履歴

---

## 📜 ライセンス

社内利用を想定しています。外部公開の際は担当者にご確認ください。

---

**最終更新: 2025年11月28日**
