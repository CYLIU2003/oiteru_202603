# 🍬 OITERU システム取扱説明書

<div align="center">

**ICカードをかざすだけで、お菓子が出てくる！**

📅 最終更新: 2026年1月6日

[![スタートガイド](https://img.shields.io/badge/📖_スタートガイド-QUICKSTART-6366f1?style=for-the-badge)](QUICKSTART.md)
[![HTML版](https://img.shields.io/badge/🌐_HTML版-おすすめ-22c55e?style=for-the-badge)](QUICKSTART.html)

</div>

---

## 📚 このドキュメントについて

OITERUシステムの詳細な説明書です。

> 💡 **すぐに始めたい人は [QUICKSTART.html](QUICKSTART.html) を開いてね！**  
> スマホでも見やすいデザインになっています 📱

---

## 🎯 OITERUって何？

ICカード（社員証・学生証など）をかざすと、**お菓子が自動で出てくる**システムです。

```
   ┌─────────────┐                ┌────────────┐
   │   ICカード   │  ───ピッ───▶  │   子機     │  ───▶  🍬 お菓子！
   │  (社員証等)  │                │ (ラズパイ) │
   └─────────────┘                └─────┬──────┘
                                        │
                                        ▼ 通信
                                  ┌────────────┐
                                  │   親機     │
                                  │ (サーバー) │  📊 利用履歴を管理
                                  └────────────┘
```

---

## 📦 システム構成

| 機器 | 役割 | IPアドレス |
|:---:|:---|:---:|
| 🖥️ **親機** | データベース + Webサーバー | `100.114.99.67` |
| 🔗 **従親機** | 親機DBを参照するサブサーバー | 設置場所による |
| 📡 **子機** | NFC読み取り + お菓子排出 | 設置場所による |

---

## 🚀 起動方法クイックリファレンス

### 🖥️ 親機（Windows PC）

| モード | コマンド | 用途 |
|:---:|:---|:---|
| 🐳 Docker | `docker-compose -f docker-compose.mysql.yml up -d` | 本番運用 |
| 🐍 仮想環境 | `.\venv-start.ps1 parent-mysql` | 開発向け |

### 🔗 従親機

| モード | コマンド |
|:---:|:---|
| 🐍 仮想環境 | `.\venv-start.ps1 sub-parent` |
| 🐳 Docker | `./docker-start.sh external` |

### 📡 子機（Raspberry Pi）

| モード | コマンド |
|:---:|:---|
| ⚡ クイック起動 | `sudo ./quick_start_unit.sh 100.114.99.67` |
| 🐍 仮想環境 | `./venv-start.sh unit` |

---

## ⚙️ 管理画面

```
🌐 http://100.114.99.67:5000/admin
🔑 パスワード: admin
```

### できること

| メニュー | 説明 |
|:---|:---|
| 👥 ユーザー管理 | ユーザーの登録・編集、在庫調整 |
| 🤖 子機管理 | 子機の登録・接続状態確認 |
| 📜 利用履歴 | 誰がいつ使ったか確認 |
| ⚙️ 設定 | 自動登録モード、1日の上限数など |

---

## 📁 ファイル構成

```
oiteru_250827_restAPI/
├── 📄 server.py           ← 親機/従親機サーバー
├── 📄 unit.py             ← 子機クライアント
├── ⚙️ config.json         ← 子機の設定
│
├── 📂 scripts/            ← 便利スクリプト
│   ├── 🚀 launcher.bat    ← ランチャー（おすすめ！）
│   └── ⚡ quick_start_*.sh
│
├── 📂 docker/             ← Docker設定
├── 📂 templates/          ← Web画面
└── 📂 取説書/             ← 📖 このドキュメント
```

---

## 📖 詳細ドキュメント

| ドキュメント | 説明 |
|:---|:---|
| 📱 [QUICKSTART.html](QUICKSTART.html) | **おすすめ！** スマホ対応のスタートガイド |
| 📝 [QUICKSTART.md](QUICKSTART.md) | マークダウン版のスタートガイド |

---

<div align="center">

**質問があれば遠慮なく聞いてね！** 😊

</div>

---

## 📚 詳細ドキュメント

- [QUICKSTART.md](QUICKSTART.md) - 起動手順（おすすめ！）

---

**質問があれば遠慮なく聞いてね！** 😊
