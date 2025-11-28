# 🍬 OITERU (オイテル) システム

**NFCカードで「お菓子」を管理するスマートIoTシステム**

社員証や学生証などのICカードをかざすだけで、自動でお菓子を取り出し、利用履歴を記録します。

---

## ⚡ クイックスタート

### 親機(サーバー)の起動

```bash
# MySQL版を起動(推奨)
docker-compose -f docker-compose.mysql.yml up -d

# または複数親機構成(同一マシン上)
docker-compose -f docker-compose.multi-server.yml up -d
```

管理画面: http://localhost:5000/admin (パスワード: `admin`)

### 子機(Raspberry Pi)の起動

```bash
# GUIモードで起動
sudo python unit_client.py

# CUIモードで起動
sudo python unit_client.py --no-gui
```

---

## 📁 主要ファイル

### 実行スクリプト (scripts/)

| スクリプト | 説明 |
|-----------|------|
| `open_mysql_port_windows.ps1` | **新規** Windowsファイアウォールでポート3306を開く |
| `open_mysql_port_linux.sh` | **新規** Linuxファイアウォールでポート3306を開く |
| `check_mysql_port.ps1` | **新規** MySQL接続状態をチェック |
| `auto_attach_card_reader.sh` | NFCリーダーの自動接続(WSL2用) |

### Docker設定ファイル

| ファイル | 用途 |
|---------|------|
| `docker-compose.mysql.yml` | **推奨** MySQL版(本番環境) |
| `docker-compose.multi-server.yml` | **新機能** 複数親機構成(同一マシン) |
| `docker-compose.external-db.yml` | **新機能** 外部MySQL接続(別マシン) |
| `docker-compose.yml` | SQLite版(開発・テスト用) |

### Pythonスクリプト

| スクリプト | 説明 |
|-----------|------|
| `app.py` | Flask REST APIサーバー(親機) |
| `unit_client.py` | 子機クライアント |
| `db_adapter.py` | **新規** データベース抽象化レイヤー(SQLite/MySQL対応) |
| `data_viewer.py` | データビューアー |
| `diagnostics.py` | システム診断 |
| `test_sensor.py` | センサーテストツール |

---

## 🚀 基本的な使い方

### 1. 初期セットアップ

**必要なもの:**
- Docker Desktop (親機)
- Raspberry Pi (子機)
- NFCカードリーダー(Sony PaSoRi RC-S380推奨)

**親機セットアップ:**
```bash
# リポジトリをクローン
git clone https://github.com/CYLIU2003/oiteru_250827_restAPI
cd oiteru_250827_restAPI

# 起動(MySQL版)
docker-compose -f docker-compose.mysql.yml up -d
```

**子機セットアップ:**
```bash
# Raspberry Piで実行
cd oiteru_250827_restAPI
sudo python unit_client.py
```

### 2. ユーザー登録

1. ブラウザで http://localhost:5000 を開く
2. 「利用者登録」をクリック
3. ICカードをリーダーにかざす
4. 情報を入力して登録

### 3. お菓子の利用

子機でICカードをかざすと自動的に:
- ユーザー認証
- 在庫数チェック
- モーター動作(お菓子の排出)
- 利用履歴の記録

### 4. 管理画面

http://localhost:5000/admin (パスワード: `admin`)

**できること:**
- ユーザー管理
- 子機管理
- 利用履歴の確認
- データのバックアップ/復元
- 利用状況の可視化
- システム診断情報の確認

---

## 📊 主な機能

### ✅ 基本機能
- NFCカードによる認証
- 自動お菓子排出(モーター制御)
- 利用履歴の記録
- Web管理画面

### ✅ 高度な機能
- **複数親機対応** - 複数の親機で同じMySQLデータベースを共有
- **外部MySQL接続** - 別マシンのMySQLサーバーに接続
- **MySQL/SQLite対応** - データベースエンジンを選択可能
- **Tailscale対応** - リモートアクセス可能
- **システム診断** - 起動時自動診断機能
- **センサー機能** - 詰まり検知(LBR-127HLD)
- **Docker対応** - 簡単デプロイ
- **未登録子機の自動探知** - 新しい子機を自動的に検出

---

## 🏗️ システム構成

### シングル親機構成
```
┌─────────────┐
│  Webブラウザ │ ← http://localhost:5000/admin
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────────┐
│  親機(Flask) │ ──  │  MySQL DB    │
│  REST API   │     │  (データ保存) │
└──────┬──────┘     └──────────────┘
       │
       │ HTTP/JSON
       │
┌──────▼────────────┐
│  子機(Raspberry Pi)│
│  - NFCリーダー     │
│  - モーター       │
│  - センサー       │
└───────────────────┘
```

### 複数親機構成 (新機能)
```
┌────────────┐  ┌────────────┐  ┌────────────┐
│ 親機1号機   │  │ 親機2号機   │  │ 親機3号機   │
│ :5000      │  │ :5001      │  │ (外部PC)   │
└─────┬──────┘  └─────┬──────┘  └─────┬──────┘
      │               │               │
      └───────────────┼───────────────┘
                      │
                ┌─────▼──────┐
                │  MySQL DB  │ ← ポート3306
                │  (共有)    │
                └────────────┘
```

---

## 🛠️ 高度な使い方

### 複数親機の構成

**同一マシン上で複数親機:**
```bash
# 親機1号機(:5000) と 親機2号機(:5001) を起動
docker-compose -f docker-compose.multi-server.yml up -d

# アクセス先
# 親機1号機: http://localhost:5000
# 親機2号機: http://localhost:5001
# phpMyAdmin: http://localhost:8080
```

**別マシンから外部MySQLに接続:**

1. **メインサーバー側でファイアウォールを開く:**
```bash
# Linux
sudo bash scripts/open_mysql_port_linux.sh
```

2. **クライアント側(Windows)でファイアウォールを開く:**
```powershell
# PowerShellを管理者権限で実行
.\scripts\open_mysql_port_windows.ps1
```

3. **接続をテスト:**
```powershell
.\scripts\check_mysql_port.ps1 -TargetHost <メインサーバーのIP>
```

4. **docker-compose.external-db.ymlを編集:**
```yaml
environment:
  - MYSQL_HOST=<メインサーバーのIP>  # 例: 100.114.99.67
  - SERVER_NAME=親機2号機(外部)
  - SERVER_LOCATION=7号館1階
```

5. **外部親機を起動:**
```bash
docker-compose -f docker-compose.external-db.yml up -d
```

詳細は [ADVANCED.md](取説書/ADVANCED.md) を参照してください:

- **複数親機構成の詳細** - セキュリティ設定、トラブルシューティング
- **MySQL移行** - SQLiteからMySQLへの移行手順
- **リモートアクセス** - Tailscale経由でのアクセス
- **API仕様** - REST API の詳細
- **カスタマイズ** - システムの拡張方法

---

## ❓ トラブルシューティング

| 問題 | 解決方法 |
|------|---------|
| 親機に繋がらない | `docker-compose logs` でログ確認 |
| MySQL接続エラー | `.\scripts\check_mysql_port.ps1 -TargetHost <IP>` で確認 |
| ポート3306がブロックされる | `.\scripts\open_mysql_port_windows.ps1` 実行(管理者権限) |
| NFCリーダーが動かない | `./scripts/auto_attach_card_reader.sh` 実行 |
| Permission denied | `sudo` を付けて実行 |
| データが見えない | `python data_viewer.py export-all` で確認 |

詳細は [TROUBLESHOOTING.md](取説書/TROUBLESHOOTING.md) を参照してください。

---

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [README.md](README.md) | このファイル(基本ガイド) |
| [ADVANCED.md](取説書/ADVANCED.md) | 上級者向け詳細ガイド(複数親機構成など) |
| [TROUBLESHOOTING.md](取説書/TROUBLESHOOTING.md) | トラブルシューティング |
| [CHANGELOG.md](取説書/CHANGELOG.md) | 更新履歴 |

---

## 🔧 よく使うコマンド

### 親機

```bash
# 起動(MySQL版)
docker-compose -f docker-compose.mysql.yml up -d

# 起動(複数親機構成)
docker-compose -f docker-compose.multi-server.yml up -d

# 停止
docker-compose down

# ログ確認
docker-compose logs -f

# データビューアー
python data_viewer.py export-all

# システム診断
python diagnostics.py
```

### 子機

```bash
# 起動(GUI)
sudo python unit_client.py

# 起動(CUI)
sudo python unit_client.py --no-gui

# 自動親機探知
sudo python unit_client.py --find-server

# センサーテスト
sudo python unit_client.py --test-sensor
```

### ファイアウォール設定

```powershell
# Windows: ポート3306を開く(管理者権限)
.\scripts\open_mysql_port_windows.ps1

# Windows: 接続をテスト
.\scripts\check_mysql_port.ps1 -TargetHost 100.114.99.67
```

```bash
# Linux: ポート3306を開く
sudo bash scripts/open_mysql_port_linux.sh
```

---

## 📦 必要なソフトウェア

### 親機
- Docker Desktop
- Git
- PowerShell 5.1以上 (Windows)

### 子機
- Raspberry Pi OS
- Python 3.7+
- NFCライブラリ(`nfcpy`)
- GPIOライブラリ(`RPi.GPIO`)

---

## 🎓 学習リソース

初めて使う方は、以下の順番で進めることをお勧めします:

1. **このREADME** - 基本的な使い方を理解
2. **実際に動かす** - 親機と子機を起動してみる
3. **ADVANCED.md** - 複数親機構成や詳しい機能を学ぶ
4. **TROUBLESHOOTING.md** - 問題が起きたら参照

---

## 🔄 更新履歴

### v2.5.0 (2025-11-28)
- **新機能**: 複数親機構成のサポート
- **新機能**: 外部MySQL接続機能
- **新規スクリプト**: ポート3306開放スクリプト (Windows/Linux)
- **新規スクリプト**: MySQL接続チェックツール
- **改善**: データベース抽象化レイヤー (db_adapter.py)
- **改善**: Dockerfileの最適化
- **ドキュメント**: ADVANCED.mdに複数親機構成の詳細を追加

詳細は [CHANGELOG.md](取説書/CHANGELOG.md) を参照してください。

---

## 📜 ライセンス

社内利用を想定しています。外部公開の際は担当者にご確認ください。

---

**最終更新: 2025年11月28日**
