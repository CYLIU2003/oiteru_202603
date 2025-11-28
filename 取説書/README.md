# 🍬 OITELU (オイテル) システム

**〜 NFCカードで「お菓子」を管理するスマートIoTシステム 〜**

OITELUは、Raspberry PiとNFC技術を活用した、お菓子の在庫管理・提供システムです。
社員証や学生証などのICカードをかざすだけで、自動でお菓子を取り出したり、利用履歴を記録したりすることができます。

**新機能**: 複数の親機が同じデータベースを共有できるようになりました！

---

## 📚 目次

- [✨ 特徴](#-特徴)
- [🔰 はじめに（初心者向けガイド）](#-はじめに初心者向けガイド)
    - [1. 全体の流れ](#1-全体の流れ)
    - [2. ネットワークの準備 (Tailscale)](#2-ネットワークの準備-tailscale)
    - [3. 親機（サーバー）のセットアップ](#3-親機サーバーのセットアップ)
    - [4. 子機（クライアント）のセットアップ](#4-子機クライアントのセットアップ)
- [🏢 複数親機構成（新機能）](#-複数親機構成新機能)
- [🚀 使い方](#-使い方)
- [🛠️ 開発者向け詳細情報](#️-開発者向け詳細情報)
- [❓ トラブルシューティング](#-トラブルシューティング)

---

## ✨ 特徴

*   **簡単操作**: ICカードをかざすだけのシンプル操作。
*   **Web管理**: ブラウザから在庫状況や利用履歴をリアルタイムで確認。
*   **どこでも接続**: Tailscale VPNを利用し、離れた場所にある親機と子機も安全に接続。
*   **Docker対応**: 面倒な環境構築は不要。コマンド一つでサーバーが立ち上がります。
*   **複数親機対応** ⭐ **NEW**: 複数の親機が同じMySQLデータベースを共有し、どこからでも同じユーザーデータにアクセス可能。
*   **外部MySQL接続** ⭐ **NEW**: 別マシンのMySQLサーバーに接続可能。

---

## 🔰 はじめに（初心者向けガイド）

Dockerやネットワークの専門知識がなくても大丈夫です。このガイド通りに進めれば、約30分でシステムを構築できます。

### 1. 全体の流れ

システムは大きく分けて「親機（サーバー）」と「子機（Raspberry Pi）」の2つで構成されます。

1.  **ネットワーク構築**: 親機と子機が会話できるようにします (**Tailscale**)。
2.  **親機起動**: データを管理するサーバーを立ち上げます (**Docker**)。
3.  **子機設定**: 実際に動く機械（Raspberry Pi）を設定します。

---

### 2. ネットワークの準備 (Tailscale)

親機と子機を安全に接続するために、無料のVPNサービス「Tailscale」を使用します。

#### 2-1. アカウント作成
1.  [Tailscale公式サイト](https://tailscale.com/) にアクセスし、「Get Started」からアカウントを作成します。

#### 2-2. 親機（PC）へのインストール
1.  親機となるPCに Tailscale アプリをインストールし、ログインします。
2.  **重要**: Tailscale上のIPアドレス（例: `100.x.y.z`）をメモしてください。これが親機の住所になります。

#### 2-3. 子機（Raspberry Pi）へのインストール
Raspberry Piのターミナルで以下を実行します。

```bash
# インストール
curl -fsSL https://tailscale.com/install.sh | sh

# 起動とログイン（表示されるURLにPCからアクセスして承認）
sudo tailscale up
```

---

### 3. 親機（サーバー）のセットアップ

親機は **Docker** を使って動かします。

#### 3-1. 準備するもの
*   **Docker Desktop**: [公式サイト](https://www.docker.com/products/docker-desktop/)からインストール。
*   このプロジェクトのファイル一式。

#### 3-2. サーバーの起動

**シングル親機構成（基本）:**
```bash
# MySQL版（推奨）
docker-compose -f docker-compose.mysql.yml up -d

# SQLite版（開発・テスト用）
docker-compose up -d
```

**複数親機構成（同一マシン）:**
```bash
# 親機1号機(:5000) と 親機2号機(:5001) を同時起動
docker-compose -f docker-compose.multi-server.yml up -d
```

起動したら、ブラウザで `http://localhost:5000` にアクセスしてみましょう。管理画面が表示されれば成功です！🎉

> **Memo**: サーバーを停止したいときは `docker-compose down` と入力します。

---

### 4. 子機（クライアント）のセットアップ

Raspberry Pi（子機）の設定を行います。

#### 4-1. スクリプトのダウンロード
プロジェクトフォルダをRaspberry Piにコピーします。

#### 4-2. 子機の起動（自動セットアップ）
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

#### 4-3. 親機の設定
起動後、選択肢が表示されます：
```
1. そのまま起動
2. 設定メニューを開く
3. 親機を自動探知して起動
```

**推奨**: `3` を選択すると、ネットワーク上の親機を自動で見つけてくれます！

手動設定する場合は、`2`を選択してサーバーURLに親機のTailscale IPアドレスを入力：
```
サーバーURL: http://100.100.10.10:5000
子機名: unit-01
```

#### 4-4. 完全自動起動
次回以降、設定済みの状態で即座に起動するには：
```bash
python unit_client.py --no-gui --auto
```

---

## 🏢 複数親機構成（新機能）

複数の場所に親機を設置し、同じユーザーデータベースを共有できます。

### 構成パターン

#### パターンA: 同一マシン上で複数親機

**使用ファイル**: `docker-compose.multi-server.yml`

```bash
# 起動
docker-compose -f docker-compose.multi-server.yml up -d

# アクセス先
# 親機1号機: http://localhost:5000
# 親機2号機: http://localhost:5001
# phpMyAdmin: http://localhost:8080
```

#### パターンB: 別マシンから外部MySQLに接続

**1. メインサーバー側でファイアウォールを開く:**

```bash
# Linux (Ubuntu/CentOS/RHEL)
sudo bash scripts/open_mysql_port_linux.sh
```

**2. クライアント側(Windows)でファイアウォールを開く:**

```powershell
# PowerShellを管理者権限で実行
.\scripts\open_mysql_port_windows.ps1
```

**3. 接続をテスト:**

```powershell
# MySQL接続状態をチェック
.\scripts\check_mysql_port.ps1 -TargetHost <メインサーバーのIP>
```

**4. docker-compose.external-db.ymlを編集:**

```yaml
environment:
  - MYSQL_HOST=100.114.99.67  # メインサーバーのIPに変更
  - SERVER_NAME=親機2号機(外部)
  - SERVER_LOCATION=7号館1階
```

**5. 外部親機を起動:**

```bash
docker-compose -f docker-compose.external-db.yml up -d
```

詳細は [ADVANCED.md](ADVANCED.md) の「複数親機構成」セクションを参照してください。

---

## 🚀 使い方

1.  **ユーザー登録**: 親機の管理画面 (`http://localhost:5000`) の「新規登録」から、ICカードを登録します。
2.  **利用**: 子機のリーダーにカードをかざします。
3.  **確認**: 登録済みユーザーならモーターが動作し、管理画面の履歴に記録されます。

---

## 🛠️ 開発者向け詳細情報

### ディレクトリ構成

```
oiteru_250827_restAPI/
├── app.py                          # 親機: Flaskサーバー本体
├── unit_client.py                  # 子機: NFC・モーター制御クライアント
├── db_adapter.py                   # データベース抽象化レイヤー(NEW)
├── docker-compose.yml              # SQLite版
├── docker-compose.mysql.yml        # MySQL版（推奨）
├── docker-compose.multi-server.yml # 複数親機構成(NEW)
├── docker-compose.external-db.yml  # 外部MySQL接続(NEW)
├── Dockerfile                      # 親機用Dockerイメージ
├── Dockerfile.mysql                # 親機用Dockerイメージ(MySQL版)
├── requirements.txt                # 親機依存ライブラリ
├── requirements.mysql.txt          # 親機依存ライブラリ(MySQL版)
├── oiteru.sqlite3                  # データベース(SQLite)
├── scripts/
│   ├── open_mysql_port_windows.ps1 # Windows: ポート3306を開く(NEW)
│   ├── open_mysql_port_linux.sh    # Linux: ポート3306を開く(NEW)
│   └── check_mysql_port.ps1        # MySQL接続チェック(NEW)
└── templates/                      # Web画面テンプレート
```

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

#### 方法1: データエクスポート（推奨）

親機でExcel形式にエクスポートして共有します。

```bash
# 全データをExcel出力
python data_viewer.py export-all

# 出力されたExcelファイルをOneDrive/Google Driveで共有
```

#### 方法2: Tailscaleリモートアクセス

親機の管理画面にリモートアクセスします。

1. Tailscaleで同じアカウントにログイン
2. ブラウザで `http://100.x.x.x:5000/admin` にアクセス
3. データをリアルタイムで確認・ダウンロード

#### 方法3: 複数親機構成（新機能）

複数の場所から同じデータベースにアクセスします。

1. メインサーバーで複数親機構成を起動
2. 各拠点から外部MySQL接続でアクセス
3. リアルタイムでデータを共有

詳細は [ADVANCED.md](ADVANCED.md) を参照してください。

---

## ❓ トラブルシューティング

| 現象 | 確認事項 |
| :--- | :--- |
| **親機に繋がらない** | Tailscaleが親機・子機両方で「Connected」になっていますか？<br>親機のファイアウォール設定を確認してください。 |
| **MySQL接続エラー** | `.\scripts\check_mysql_port.ps1 -TargetHost <IP>` で確認<br>ポート3306がファイアウォールで開いていますか？ |
| **ポート3306がブロックされる** | `.\scripts\open_mysql_port_windows.ps1` を管理者権限で実行 |
| **NFCリーダーが動かない** | USBケーブルはしっかり刺さっていますか？<br>WSL2の場合、`usbipd attach` を忘れていませんか？ |
| **Permission denied** | Raspberry PiでGPIOを操作するには権限が必要です。<br>`sudo python unit_client.py` で実行してみてください。 |
| **データが見られない** | `data_viewer.py`を使用してExcel出力してください。 |

詳しくは [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

---

## 📚 関連ドキュメント

- [ADVANCED.md](ADVANCED.md) - **上級者向け詳細ガイド** (複数親機構成、API仕様など)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング
- [CHANGELOG.md](CHANGELOG.md) - 更新履歴
- [DIAGNOSTICS.md](DIAGNOSTICS.md) - システム診断機能
- [DOCKER_UNIT.md](DOCKER_UNIT.md) - Docker対応の詳細

---

## 📜 ライセンス

社内利用を想定しています。外部公開の際は担当者にご確認ください。

---

**最終更新: 2025年11月28日**
