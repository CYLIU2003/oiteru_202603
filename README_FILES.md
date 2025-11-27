# ファイル構造ガイド - OITELUプロジェクト

## 📁 主要ファイル

### 🖥️ 親機(サーバー)関連

| ファイル | 説明 |
|---------|------|
| `app.py` | **Flaskメインアプリケーション** (MySQL対応済み) |
| `db_adapter.py` | **データベース抽象化レイヤー** (SQLite/MySQL両対応) |
| `diagnostics.py` | システム診断モジュール (起動時チェック) |
| `data_viewer.py` | データベース閲覧ツール (Excel出力) |
| `oiteru.sqlite3` | SQLiteデータベース (ローカルモード用) |

### 🤖 子機(クライアント)関連

| ファイル | 説明 |
|---------|------|
| `unit_client.py` | **子機メインスクリプト** (Raspberry Pi用) |
| `nfc_reader_client.py` | NFCリーダー専用クライアント |
| `unit_client_watchdog.sh` | 子機自動再起動スクリプト |
| `oiteru-unit.service` | systemdサービス設定 |

### 🐳 Docker関連

| ファイル | 説明 | 使用方法 |
|---------|------|---------|
| `docker-compose.yml` | **SQLite版** Docker設定 | `docker-compose up -d` |
| `docker-compose.mysql.yml` | **MySQL版** Docker設定 | `docker-compose -f docker-compose.mysql.yml up -d` |
| `docker-compose.unit.yml` | 子機用Docker設定 | `docker-compose -f docker-compose.unit.yml up -d` |
| `Dockerfile` | 親機用イメージ定義 | |
| `Dockerfile.unit` | 子機用イメージ定義 | |

### 📦 依存関係

| ファイル | 説明 |
|---------|------|
| `requirements.txt` | Python依存関係 (SQLite版) |
| `requirements.mysql.txt` | Python依存関係 (MySQL版) |
| `requirements-client.txt` | 子機用Python依存関係 |

### 🗄️ データベース初期化

| ファイル | 説明 |
|---------|------|
| `init_mysql.sql` | MySQL初期化スクリプト |

### 🛠️ ユーティリティスクリプト

| ファイル | 説明 | プラットフォーム |
|---------|------|----------------|
| `start_oiteru.sh` | 親機起動スクリプト | Linux/Mac |
| `start_oiteru.ps1` | 親機起動スクリプト | Windows |
| `start_unit.sh` | 子機起動スクリプト | Linux/Raspberry Pi |
| `attach_card_reader.ps1` | USB NFCリーダー接続 | Windows → WSL2 |
| `init_card_reader.sh` | NFCリーダー初期化 | Linux/Docker |
| `test_nfc_in_container.sh` | NFCテストスクリプト | Docker |

### 📚 ドキュメント

| ファイル/フォルダ | 説明 |
|-----------------|------|
| `MYSQL_MIGRATION.md` | **MySQL移行ガイド** (複数親機対応) |
| `取説書/` | 詳細マニュアル集 |
| `注釈付コード/` | コード解説 |
| `.github/copilot-instructions.md` | AI開発アシスタント用指示 |

### 🗂️ Web UI

| フォルダ | 説明 |
|---------|------|
| `templates/` | HTMLテンプレート |
| `static/` | CSS/画像などの静的ファイル |

### 🗄️ アーカイブ

| フォルダ | 説明 |
|---------|------|
| `archive/backup/` | データベースバックアップ |
| `archive/old_scripts/` | 古いスクリプト・一時ファイル |
| `archive/temp_files/` | 一時ファイル (desktop.iniなど) |

## 🚀 クイックスタート

### SQLiteモード(単一親機)
```bash
docker-compose up -d
```

### MySQLモード(複数親機対応)
```bash
docker-compose -f docker-compose.mysql.yml up -d --build
```

### 子機起動(Raspberry Pi)
```bash
python unit_client.py
```

## 📖 詳細ドキュメント

- **MySQL移行**: `MYSQL_MIGRATION.md`
- **完全マニュアル**: `取説書/MANUAL.md`
- **トラブルシューティング**: `取説書/TROUBLESHOOTING.md`
- **実装詳細**: `取説書/IMPLEMENTATION.md`

## 🔧 設定ファイル

| ファイル | 説明 |
|---------|------|
| `config.json` | アプリケーション設定 |
| `.dockerignore` | Docker除外ファイル |
| `.gitignore` | Git除外ファイル |

## 🗑️ 不要なファイルを削除した場合の復元

`archive/`フォルダから復元可能:
```bash
cp archive/old_scripts/[ファイル名] .
```
