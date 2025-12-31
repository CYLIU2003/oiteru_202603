# 🍬 OITERU システム取扱説明書

**最終更新: 2025年12月31日**

---

## 📚 このドキュメントについて

OITERUシステムの詳細な説明書です。  
**すぐに始めたい人は [QUICKSTART.md](QUICKSTART.md) を見てね！**

---

## 🎯 OITERUって何？

ICカード（社員証・学生証など）をかざすと、お菓子が自動で出てくるシステムです。

---

## 📦 システム構成

| 機器 | 役割 | IPアドレス |
|:---:|:---|:---|
| **親機** | データベース + Webサーバー | `100.114.99.67` |
| **従親機** | 親機DBを参照するサブサーバー | 設置場所による |
| **子機** | NFC読み取り + お菓子排出 | 設置場所による |

---

## 🚀 起動方法

### 親機（Windows PC）

| モード | コマンド | 説明 |
|:---|:---|:---|
| **Docker（推奨）** | `docker-compose -f docker-compose.mysql.yml up -d` | 本番運用向け |
| **仮想環境** | `.\venv-start.ps1 parent-mysql` | 開発向け |
| **通常（非推奨）** | `python server.py` | テスト用 |

### 従親機

| モード | コマンド |
|:---|:---|
| **仮想環境** | `.\venv-start.ps1 sub-parent` |
| **Docker** | `./docker-start.sh external` |

### 子機（Raspberry Pi）

| モード | コマンド |
|:---|:---|
| **クイック起動** | `sudo ./quick_start_unit.sh 100.114.99.67` |
| **仮想環境** | `./venv-start.sh unit` |

---

## 🖥️ 管理画面

```
http://100.114.99.67:5000/admin
パスワード: admin
```

---

## 📁 ファイル構成

```
oiteru_250827_restAPI/
├── server.py           ← 親機/従親機サーバー
├── unit.py             ← 子機クライアント
├── config.json         ← 子機の設定
│
├── scripts/            ← 便利スクリプト
│   ├── launcher.bat    ← ランチャー
│   └── quick_start_*.sh
│
├── docker/             ← Docker設定
├── templates/          ← Web画面
└── 取説書/             ← このドキュメント
```

---

## 📚 詳細ドキュメント

- [QUICKSTART.md](QUICKSTART.md) - 起動手順（おすすめ！）

---

**質問があれば遠慮なく聞いてね！** 😊
