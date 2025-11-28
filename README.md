# 🍬 OITERU (オイテル) システム

**NFCカードで「お菓子」を管理するスマートIoTシステム**

社員証や学生証などのICカードをかざすだけで、自動でお菓子を取り出し、利用履歴を記録します。

---

## ⚡ クイックスタート

### 親機(サーバー)の起動

```bash
# MySQL版を起動(推奨)
./scripts/start_oiteru_mysql.sh

# またはDocker Composeで直接起動
docker-compose -f docker-compose.mysql.yml up -d
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
| `start_oiteru_mysql.sh` | 親機(MySQL版)を起動 |
| `start_unit.sh` | 子機を起動 |
| `setup_multi_server.sh` | 複数親機構成のセットアップ |
| `auto_attach_card_reader.sh` | NFCリーダーの自動接続(WSL2用) |

### Docker設定ファイル

| ファイル | 用途 |
|---------|------|
| `docker-compose.mysql.yml` | **推奨** MySQL版(本番環境) |
| `docker-compose.multi-server.yml` | 複数親機構成 |
| `docker-compose.external-db.yml` | 外部MySQL接続 |

### Pythonスクリプト

| スクリプト | 説明 |
|-----------|------|
| `app.py` | Flask REST APIサーバー(親機) |
| `unit_client.py` | 子機クライアント |
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
git clone <repository-url>
cd oiteru_250827_restAPI

# 起動
./scripts/start_oiteru_mysql.sh
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

---

## 📊 主な機能

### ✅ 基本機能
- NFCカードによる認証
- 自動お菓子排出(モーター制御)
- 利用履歴の記録
- Web管理画面

### ✅ 高度な機能
- **複数親機対応** - 複数の親機で同じデータベースを共有
- **MySQL対応** - SQLiteまたはMySQLを選択可能
- **Tailscale対応** - リモートアクセス可能
- **システム診断** - 自動診断機能
- **センサー機能** - 詰まり検知(LBR-127HLD)
- **Docker対応** - 簡単デプロイ

---

## 🏗️ システム構成

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

---

## 🛠️ 高度な使い方

詳細は [ADVANCED.md](ADVANCED.md) を参照してください:

- **複数親機構成** - 複数の場所に親機を設置
- **MySQL移行** - SQLiteからMySQLへの移行
- **リモートアクセス** - Tailscale経由でのアクセス
- **API仕様** - REST API の詳細
- **カスタマイズ** - システムの拡張方法

---

## ❓ トラブルシューティング

| 問題 | 解決方法 |
|------|---------|
| 親機に繋がらない | `docker-compose logs` でログ確認 |
| NFCリーダーが動かない | `./scripts/auto_attach_card_reader.sh` 実行 |
| Permission denied | `sudo` を付けて実行 |
| データが見えない | `python data_viewer.py export-all` で確認 |

詳細は [TROUBLESHOOTING.md](TROUBLESHOOTING.md) を参照してください。

---

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [README.md](README.md) | このファイル(基本ガイド) |
| [ADVANCED.md](ADVANCED.md) | 上級者向け詳細ガイド |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | トラブルシューティング |

---

## 🔧 よく使うコマンド

### 親機

```bash
# 起動
docker-compose -f docker-compose.mysql.yml up -d

# 停止
docker-compose -f docker-compose.mysql.yml down

# ログ確認
docker-compose logs -f

# データビューアー
python data_viewer.py export-all
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

---

## 📦 必要なソフトウェア

### 親機
- Docker Desktop
- Git

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
3. **ADVANCED.md** - より詳しい機能を学ぶ
4. **TROUBLESHOOTING.md** - 問題が起きたら参照

---

## 🔄 更新履歴

最新の変更は [CHANGELOG](CHANGELOG.md) を参照してください。

---

## 📜 ライセンス

社内利用を想定しています。外部公開の際は担当者にご確認ください。

---

**最終更新: 2025年11月28日**
