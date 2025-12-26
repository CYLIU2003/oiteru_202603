# OITELU システムランチャー

親機・従親機・子機を簡単に起動できる統合ランチャーです。

## 📁 ファイル構成

```
scripts/
  launcher_utils.py       # 共通ユーティリティモジュール
  launcher_gui.py         # GUI版ランチャー（Tkinter）
  launcher_cui.py         # CUI版ランチャー（BIOS風）
  launcher_config.json    # ランチャー設定ファイル
  launcher.bat            # Windows起動スクリプト（バッチ）
  launcher.ps1            # Windows起動スクリプト（PowerShell）
  launcher.sh             # Linux/Mac起動スクリプト
  LAUNCHER_README.md      # このファイル
```

## 🚀 クイックスタート

### Windows

#### 方法1: バッチファイル（ダブルクリック）
```batch
cd scripts
launcher.bat
```

#### 方法2: PowerShell
```powershell
cd scripts
.\launcher.ps1
```

#### 方法3: 直接実行
```batch
cd scripts

# GUI版
python launcher_gui.py

# CUI版
python launcher_cui.py
```

### Linux / Mac

```bash
cd scripts

# 実行権限を付与
chmod +x launcher.sh

# 起動
./launcher.sh
```

または直接実行：

```bash
cd scripts

# GUI版
python3 launcher_gui.py

# CUI版
python3 launcher_cui.py
```

## 🎨 GUI版ランチャー

### 特徴
- 🖼️ **グラフィカルインターフェース**: 直感的な操作が可能
- 📺 **リアルタイムターミナル**: プロセスの出力をリアルタイム表示
- ⚙️ **詳細設定画面**: サーバー名、ポート、MySQL設定などを簡単に変更
- 🔍 **環境チェック機能**: Python、仮想環境、Docker、ポートの状態を確認

### 主な機能

#### 起動モード選択
- **親機**: データベース管理サーバー
- **従親機**: 外部DB接続サーバー
- **子機**: NFC + モーター制御

#### 実行方法選択
- **通常モード**: 直接Python実行
- **仮想環境モード**: .venv内のPythonで実行
- **Dockerモード**: Dockerコンテナで実行

#### その他の機能
- 環境チェック
- 依存パッケージの自動インストール
- 詳細設定（サーバー名、ポート、MySQL、子機設定など）
- ログのリアルタイム表示とクリア
- **カードリーダーセットアップ**: NFCカードリーダーの自動検出・接続

### 💳 カードリーダー機能

親機・従親機でもNFCカードリーダーを使用する場合、ランチャーから簡単にセットアップできます。

#### 機能
- **自動検出**: USB接続されたカードリーダーを自動検出
- **WSL対応**: Windows環境でWSLへの自動アタッチ（usbipdを使用）
- **pcscd起動**: PC/SCデーモンの自動起動と管理

#### 使い方

##### GUI版
1. `💳 カードリーダー設定` ボタンをクリック
2. 自動的にカードリーダーを検出・設定
3. ログで進行状況を確認

##### CUI版
1. メインメニューから `5 - Card Reader Setup` を選択
2. 自動的に以下を実行：
   - カードリーダーの検出
   - WSL環境へのUSBアタッチ（Windows）
   - pcscdデーモンの起動

#### 必要な環境

**Windows + WSL環境:**
- `usbipd` のインストールが必要
  ```powershell
  winget install usbipd
  ```

**Linux環境:**
- `pcscd` パッケージのインストールが必要
  ```bash
  # Ubuntu/Debian
  sudo apt-get install pcscd pcsc-tools
  
  # Fedora
  sudo dnf install pcsc-lite pcsc-tools
  ```

## 💻 CUI版ランチャー（BIOS風）

### 特徴
- 🎮 **BIOS風UI**: レトロで直感的なテキストインターフェース
- 🎨 **カラフルな表示**: ANSI色を使った見やすい画面
- ⚡ **キーボード操作**: 数字キーで素早く選択

### メインメニュー

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                      OITELU SYSTEM LAUNCHER v2.0                          ║
║                      Boot Configuration Utility                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─ System Information ────────────────────────────────────────────────────┐
│ Platform      : Windows                                                  │
│ Python        : 3.11.0                                                   │
│ Hostname      : DESKTOP-EXAMPLE                                          │
│ Working Dir   : C:\Users\...\oiteru_250827_restAPI                       │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Current Configuration ─────────────────────────────────────────────────┐
│ Boot Mode     : 親機                                                     │
│ Launch Mode   : 通常モード                                               │
│ Server Name   : OITERU親機                                               │
│ Server Port   : 5000                                                     │
└──────────────────────────────────────────────────────────────────────────┘

═══ Main Menu ═══

  1 - Select Boot Mode (親機/従親機/子機)
  2 - Select Launch Mode (通常/仮想環境/Docker)
  3 - Environment Check
  4 - Install Dependencies
  5 - Advanced Settings
  6 - ► START SYSTEM ◄
  0 - Exit
```

## ⚙️ 設定ファイル（launcher_config.json）

ランチャーの設定は `launcher_config.json` に保存されます。

### 設定項目

```json
{
    "server_name": "OITERU親機",
    "server_location": "未設定",
    "parent_url": "http://localhost:5000",
    "unit_name": "DESKTOP-EXAMPLE",
    "unit_password": "password123",
    "db_type": "sqlite",
    "mysql_host": "localhost",
    "mysql_port": 3306,
    "mysql_database": "oiteru",
    "mysql_user": "oiteru_user",
    "mysql_password": "oiteru_password_2025",
    "venv_path": ".venv",
    "python_command": "python",
    "docker_compose_file": "docker-compose.yml",
    "server_port": 5000,
    "auto_install_packages": true,
    "last_mode": "normal",
    "last_role": "parent"
}
```

### 設定の変更方法

1. **GUI版**: 「⚙️ 詳細設定」ボタンから変更
2. **CUI版**: メインメニューの「5 - Advanced Settings」から変更
3. **手動編集**: `launcher_config.json` を直接編集

## 📦 依存パッケージのインストール

### 自動インストール

GUI版またはCUI版で「依存関係インストール」を選択すると、自動的に `requirements.txt` からパッケージをインストールします。

### 手動インストール

```bash
# 通常のPython環境
pip install -r requirements.txt

# 仮想環境を作成してインストール
python -m venv .venv
.venv\Scripts\activate  # Windows
# または
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## 🔍 環境チェック機能

ランチャーには環境チェック機能が搭載されています。

### チェック項目
1. **Python環境**: バージョン確認
2. **仮想環境**: .venv の検出
3. **Docker**: Dockerデーモンの状態
4. **Docker Compose**: インストール確認
5. **ポート**: 指定ポートの利用可否

## 🐳 Dockerモードについて

Dockerモードでは、以下のDocker Composeファイルが使用されます：

- **親機**: `docker-compose.yml`（SQLite使用）
- **親機（MySQL）**: `docker-compose.mysql.yml`
- **従親機**: `docker-compose.external-db.yml`
- **子機**: `docker/docker-compose.unit.yml`

### 環境変数

Dockerモードでは `.env` ファイルが自動生成されます：

```env
SERVER_NAME=OITERU親機
SERVER_LOCATION=未設定
DB_TYPE=sqlite
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=oiteru
MYSQL_USER=oiteru_user
MYSQL_PASSWORD=oiteru_password_2025
```

## 🛠️ トラブルシューティング

### 仮想環境が見つからない

```bash
# 仮想環境を作成
python -m venv .venv

# または、ランチャーから「依存関係インストール」を実行
```

### Docker起動に失敗する

```bash
# Dockerデーモンが起動しているか確認
docker ps

# Dockerを起動（Linux）
sudo service docker start

# Dockerを起動（Windows）
# Docker Desktopアプリを起動
```

### ポートが使用中

別のポート番号を使用してください：

1. GUI版: 詳細設定 → サーバーポート番号を変更
2. CUI版: Advanced Settings → Server Port を変更
3. 手動: `launcher_config.json` の `server_port` を変更

### tkinterが見つからない（Linux）

```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

## 📚 使用例

### 例1: 親機を通常モードで起動

1. ランチャーを起動: `launcher.bat` または `./launcher.sh`
2. GUI版を選択: `1`
3. 起動モード: `親機` を選択
4. 実行方法: `通常モード` を選択
5. `▶️ 起動` をクリック

### 例2: 従親機をDockerで起動（外部MySQL接続）

1. ランチャーを起動
2. CUI版を選択: `2`
3. `1 - Select Boot Mode` → `2 - Sub Parent Server`
4. `2 - Select Launch Mode` → `3 - Docker Mode`
5. `5 - Advanced Settings` → `6 - MySQL Settings` で接続情報を設定
6. `9 - Save Settings` で保存
7. `6 - START SYSTEM` で起動

### 例3: 子機を仮想環境で起動

1. ランチャーを起動
2. GUI版を選択
3. 起動モード: `子機` を選択
4. 実行方法: `仮想環境モード` を選択
5. `⚙️ 詳細設定` → `子機設定` タブで親機URLなどを設定
6. `💾 保存` で保存
7. `📦 依存関係インストール` で仮想環境を作成・パッケージをインストール
8. `▶️ 起動` で起動

## 🎯 高度な使い方

### カスタムDocker Composeファイルの使用

`launcher_config.json` で指定できます：

```json
{
    "docker_compose_file": "docker-compose.custom.yml"
}
```

### 異なる設置場所・名前

サーバー名と設置場所を変更することで、複数のサーバーを識別できます：

```json
{
    "server_name": "OITERU親機（本部）",
    "server_location": "東京本社 1階"
}
```

### 仮想環境のパスを変更

デフォルトは `.venv` ですが、変更可能です：

```json
{
    "venv_path": "my_custom_venv"
}
```

## 📄 ライセンス

このプロジェクトは OITELU システムの一部です。

## 🤝 サポート

問題が発生した場合は、以下を確認してください：

1. `launcher_config.json` の設定が正しいか
2. 必要な依存パッケージがインストールされているか
3. Docker（使用する場合）が起動しているか
4. ポートが利用可能か

---

**OITELU System Launcher v2.0**  
親機・従親機・子機の統合起動ソリューション
