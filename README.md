# 🍬 OITERU (オイテル) システム

**NFCカードで「生理用品(ナプキン)」を管理するスマートIoTシステム**

社員証や学生証などのICカードをかざすだけで、自動で生理用品(ナプキン)を排出し、利用履歴を記録します。

---

## 📁 ファイル構成（これだけ覚えればOK！）

```
oiteru_250827_restAPI/
│
├── 🗄️  db_server.py     ← 標準の親機エントリポイント（MySQL）
├── 🖥️  server.py        ← legacy 親機エントリポイント（SQLite/互換用）
├── 📡  unit.py          ← 子機を起動するファイル（Raspberry Pi用）
│
├── 📄  db_adapter.py    ← (内部用) データベース処理
├── ⚙️  config.example.json ← 子機設定テンプレート
├── ⚙️  .env.example     ← サーバー設定のテンプレート
│
├── �  docker/          ← Docker関連ファイル
├── 📁  docs/            ← 運用資料・引き継ぎ資料
├── 📁  scripts/         ← 便利スクリプト集
├── 📁  tools/           ← テスト・診断ツール
├── 📁  templates/       ← Web画面のHTML
├── 📁  static/          ← CSS・画像
│
└── 📚  取説書/          ← ドキュメント
    ├── QUICKSTART.md    ← 🔰 初心者はここから！
    └── REFERENCE.md     ← 📖 全機能の詳細説明
```

---

## 標準構成

- 親機: `db_server.py`
- DB: `MySQL 8 (InnoDB)`
- Docker: `docker/docker-compose.mysql.yml`
- `server.py` は legacy 互換経路で、新規開発対象外です

## ⚡ 4ステップで始める

### ステップ1: `.env` を作成

```bash
cp .env.example .env
```

最低限、以下を必ず変更してください。

- `FLASK_SECRET_KEY`
- `OITERU_ADMIN_PASSWORD`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`

`OITERU_STRICT_SECURITY=true` の場合、既定値のままでは起動時に停止します。

### ステップ2: 子機設定を作成

```bash
cp config.example.json config.json
```

最低限、以下を子機ごとに変更してください。

- `SERVER_URL`
- `UNIT_NAME`
- `UNIT_PASSWORD`

### ステップ3: 親機を起動

```bash
# Dockerで起動（推奨・標準）
cd docker
docker-compose -f docker-compose.mysql.yml up -d

# または直接起動（MySQL接続）
python db_server.py
```

### ステップ4: 子機を起動（Raspberry Pi）

```bash
# 仮想環境で起動（推奨）
./venv-start.sh unit

# または直接起動（CUIモード）
sudo python unit.py --no-gui
```

### ステップ5: 管理画面にアクセス

ブラウザで http://localhost:5000/admin を開き、`.env` で設定した管理者パスワードでログインします。

---

## 📚 ドキュメント

| 対象 | ドキュメント | 説明 |
|:---:|:---|:---|
| 🔰 | [取説書/QUICKSTART.md](取説書/QUICKSTART.md) | **初心者向け** - まずはここから |
| 📖 | [取説書/REFERENCE.md](取説書/REFERENCE.md) | **上級者向け** - 全機能の詳細 |
| 🛠️ | [docs/operations.md](docs/operations.md) | **運用・引き継ぎ向け** - 日常運用と障害対応 |

---

## ✨ 主な機能

- **自動登録モード**: 未登録カードも自動でユーザー登録
- **複数親機対応**: 複数サーバーで同じDBを共有
- **Web管理画面**: ブラウザから利用状況を確認
- **Docker対応**: MySQL込みで環境構築

---

## 運用上の注意

- 標準DBは `MySQL 8 (InnoDB)` です
- `config.json`、`*.sqlite3`、`*.log` は Git 管理しません
- 管理者パスワードと Flask secret は必ず `.env` から設定してください
- `server.py + SQLite` は legacy 互換経路です。標準構成では使いません

---

**最終更新: 2026年1月12日**
