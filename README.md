<div align="center">

# OITERU

NFC カードで生理用品の利用・在庫・子機状態を管理する学内実証向け IoT システム

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20API-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Unit-C51A4A?logo=raspberrypi&logoColor=white)
![tmux](https://img.shields.io/badge/tmux-standard-1BB91F?logo=gnubash&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-not%20required-6B7280?logo=docker&logoColor=white)

</div>

OITERU は、NFC カードを用いて生理用品を管理・排出し、利用履歴・在庫・子機状態を扱う IoT システムです。

このリポジトリの標準運用は **Linux 系 OS + tmux + ローカル MySQL 8 + `db_server.py` + `unit.py`** です。しばらく Docker を使わない前提で、起動手順と運用手順を tmux 中心に整理しています。

## 必要な環境

| 区分 | 必須 / 推奨 | 内容 |
|---|---|---|
| 親機 OS | 必須 | Ubuntu 22.04 LTS 以降などの Linux 系 OS |
| 子機 OS | 必須 | Raspberry Pi OS 64-bit 推奨 |
| Python | 必須 | Python 3.10 以上 |
| DB | 必須 | MySQL 8.0 系 |
| 起動管理 | 必須 | tmux |
| Git | 必須 | Git CLI |
| エディタ | 推奨 | Visual Studio Code |
| ネットワーク | 必須 | 親機と子機が同一 LAN、または Tailscale 等で相互通信できること |

## 公式ダウンロード URL

| ソフトウェア | 用途 | URL |
|---|---|---|
| Ubuntu | 親機 Linux OS の候補 | https://ubuntu.com/download |
| Raspberry Pi Imager | Raspberry Pi OS を SD カードへ書き込む | https://www.raspberrypi.com/software/ |
| Raspberry Pi OS | 子機 OS | https://www.raspberrypi.com/software/operating-systems/ |
| Python | Python 本体 | https://www.python.org/downloads/ |
| Git | Git CLI | https://git-scm.com/downloads |
| MySQL Community Server | 親機 DB | https://dev.mysql.com/downloads/mysql/ |
| tmux | tmux 本体。Linux では通常 `apt` で入れる | https://github.com/tmux/tmux/releases |
| Visual Studio Code | 推奨エディタ | https://code.visualstudio.com/download |
| Tailscale | 別ネットワーク間で親機・子機をつなぐ場合の任意 VPN | https://tailscale.com/downloads |

Linux では、通常は次の `apt` コマンドで必要な実行環境を入れます。

```bash
sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip mysql-server curl
```

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
