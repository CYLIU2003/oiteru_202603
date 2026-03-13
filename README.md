# 🍬 OITERU (オイテル) システム

**NFCカードで「生理用品(ナプキン)」を管理するスマートIoTシステム**

社員証や学生証などのICカードをかざすだけで、自動で生理用品(ナプキン)を排出し、利用履歴を記録します。

---

## 📁 ファイル構成（これだけ覚えればOK！）

```
oiteru_250827_restAPI/
│
├── 🖥️  server.py        ← 親機を起動するファイル（登録機能付きWebサーバー）
├── 🗄️  db_server.py     ← MySQL版親機（本番環境向け）
├── 📡  unit.py          ← 子機を起動するファイル（Raspberry Pi用）
│
├── 📄  db_adapter.py    ← (内部用) データベース処理
├── �  config.json      ← 子機の設定ファイル
├── ⚙️  .env.example     ← サーバー設定のテンプレート
│
├── �  docker/          ← Docker関連ファイル
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

## ⚡ 3ステップで始める

### ステップ1: `.env` を作成

```bash
cp .env.example .env
```

最低限、以下を必ず変更してください。

- `FLASK_SECRET_KEY`
- `OITERU_ADMIN_PASSWORD`
- `MYSQL_PASSWORD`

### ステップ2: 親機を起動

```bash
# Dockerで起動（推奨・標準）
cd docker
docker-compose -f docker-compose.mysql.yml up -d

# または直接起動（MySQL接続）
python db_server.py
```

### ステップ3: 子機を起動（Raspberry Pi）

```bash
# 仮想環境で起動（推奨）
./venv-start.sh unit

# または直接起動（CUIモード）
sudo python unit.py --no-gui
```

### ステップ4: 管理画面にアクセス

ブラウザで http://localhost:5000/admin を開き、`.env` で設定した管理者パスワードでログインします。

---

## 📚 ドキュメント

| 対象 | ドキュメント | 説明 |
|:---:|:---|:---|
| 🔰 | [取説書/QUICKSTART.md](取説書/QUICKSTART.md) | **初心者向け** - まずはここから |
| 📖 | [取説書/REFERENCE.md](取説書/REFERENCE.md) | **上級者向け** - 全機能の詳細 |

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

---

**最終更新: 2026年1月12日**
