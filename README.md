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

### ステップ1: 親機を起動

```bash
# Dockerで起動（推奨）
cd docker
docker-compose -f docker-compose.mysql.yml up -d

# または直接起動（開発用）
python server.py
```

### ステップ2: 子機を起動（Raspberry Pi）

```bash
# 仮想環境で起動（推奨）
./venv-start.sh unit

# または直接起動（CUIモード）
sudo python unit.py --no-gui
```

### ステップ3: 管理画面にアクセス

ブラウザで http://localhost:5000/admin を開く  
パスワード: `admin`

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
- **Docker対応**: コマンド一つで環境構築

---

**最終更新: 2026年1月12日**
