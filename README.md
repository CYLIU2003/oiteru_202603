# OITERU システム

OITERU は、NFC カードを用いて生理用品を管理・排出し、利用履歴・在庫・子機状態を扱う IoT システムです。

このリポジトリの標準運用は **Linux 系 OS + tmux + ローカル MySQL 8 + `db_server.py` + `unit.py`** です。しばらく Docker を使わない前提で、起動手順と運用手順を tmux 中心に整理しています。

## まず読む順番

| 順番 | ファイル | 目的 |
|---:|---|---|
| 1 | `README.md` | 全体像と最短起動を確認する |
| 2 | `docs/onboarding.md` | 新しく参加した人が安全に開発へ入る |
| 3 | `取説書/QUICKSTART.md` | 親機・子機を tmux で実際に起動する |
| 4 | `docs/operations.md` | 日常運用・障害時対応・引き継ぎを見る |
| 5 | `scripts/README.md` | 使ってよいスクリプトを確認する |

## 標準構成

| 項目 | 標準 |
|---|---|
| 親機 OS | Linux 系 OS |
| 子機 OS | Raspberry Pi OS / Linux 系 OS |
| 起動方法 | `tmux` |
| 親機エントリポイント | `db_server.py` |
| 子機エントリポイント | `unit.py` |
| DB | MySQL 8 (InnoDB) |
| DB 起動 | OS の `mysql` サービス |
| 設定 | `.env` と `config.json` |

`server.py + SQLite` は legacy 互換経路です。新規セットアップ、学内実証、レビューでは使わないでください。

## 最短起動: 親機

```bash
cd ~/Desktop/oiteru_202603
git pull

sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip mysql-server

cp .env.example .env
nano .env

scripts/setup_local_mysql.sh
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

管理画面:

```text
http://<親機IP>:5000/admin
```

同じ端末で確認する場合:

```text
http://localhost:5000/admin
```

## 最短起動: 子機

```bash
cd ~/Desktop/oiteru_202603
git pull

sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip curl

cp config.example.json config.json
nano config.json

scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

`config.json` では最低限、次を子機ごとに変更してください。

| キー | 内容 | 例 |
|---|---|---|
| `SERVER_URL` | 親機 URL | `http://192.168.1.10:5000` |
| `UNIT_NAME` | 管理画面に出る子機名 | `unit-01` |
| `UNIT_PASSWORD` | 親機と合わせる子機パスワード | `change-this` |

## tmux 操作

| やりたいこと | コマンド |
|---|---|
| 親機を起動 | `scripts/tmux_oiteru.sh start parent` |
| 子機を起動 | `scripts/tmux_oiteru.sh start unit` |
| 状態を見る | `scripts/tmux_oiteru.sh status` |
| 親機に戻る | `scripts/tmux_oiteru.sh attach parent` |
| 子機に戻る | `scripts/tmux_oiteru.sh attach unit` |
| ログを見る | `scripts/tmux_oiteru.sh logs parent` |
| 停止する | `scripts/tmux_oiteru.sh stop parent` |

tmux 画面から一時退出するには `Ctrl+b` の後に `d` を押します。アプリは動き続けます。

## よく使う確認コマンド

```bash
git branch --show-current
git status --short
tmux ls
systemctl status mysql
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
curl http://localhost:5000
```

## ディレクトリ概要

```text
oiteru_202603/
├── db_server.py              # 標準の親機エントリポイント(MySQL)
├── unit.py                   # 子機エントリポイント
├── server.py                 # legacy / 従親機向け経路
├── .env.example              # 親機 .env のテンプレート
├── config.example.json       # 子機 config.json のテンプレート
├── requirements.txt          # 親機依存パッケージ
├── requirements-client.txt   # 子機依存パッケージ
├── scripts/                  # tmux 起動・初期化・診断スクリプト
├── docs/                     # 開発・運用資料
├── tests/                    # 単体テスト
└── 取説書/                   # 初心者向け手順書
```

## Git 管理しないもの

次のファイルは秘密情報やローカル状態を含むため、コミットしないでください。

| ファイル | 理由 |
|---|---|
| `.env` | 管理者パスワード、DB パスワード |
| `config.json` | 子機パスワード、設置場所、親機 URL |
| `logs/` | 運用ログ |
| `*.log` | 運用ログ |
| `*.sqlite3` | legacy DB / ローカルデータ |

## 開発の優先順位

1. 認証、DB、ログ、障害時整合性を優先する
2. 標準 DB は MySQL 8(InnoDB) とする
3. 実機依存コードは抽象化し、モックでテストできる形にする
4. route handler から直接 SQL を書かない
5. コード変更時は README、取説、`.env.example`、docs も必要に応じて更新する

詳細な開発参加手順は `docs/onboarding.md` を読んでください。

最終更新: 2026-06-04
