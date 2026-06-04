# OITERU クイック起動メモ

詳しい手順は `取説書/QUICKSTART.md` にまとめています。このファイルは、すでに概要を知っている人向けの短いメモです。

標準は **Linux 系 OS + tmux + ローカル MySQL + `db_server.py` + `unit.py`** です。Docker は標準手順では使いません。

## 1. 親機

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

## 2. 子機

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

## 3. tmux 操作

| やりたいこと | コマンド |
|---|---|
| 一時退出 | `Ctrl+b` → `d` |
| 一覧 | `tmux ls` |
| 状態確認 | `scripts/tmux_oiteru.sh status` |
| 親機に戻る | `scripts/tmux_oiteru.sh attach parent` |
| 子機に戻る | `scripts/tmux_oiteru.sh attach unit` |
| 停止 | `scripts/tmux_oiteru.sh stop <parent|unit>` |

## 4. よく使う確認

```bash
git branch --show-current
git status --short
tmux ls
systemctl status mysql
curl http://localhost:5000
```

## 5. 詳細資料

| ファイル | 内容 |
|---|---|
| `README.md` | 全体像 |
| `docs/onboarding.md` | 新入生・新規参加者向け |
| `取説書/QUICKSTART.md` | 初心者向けの詳細起動手順 |
| `取説書/README.md` | 取説書の目次 |
| `docs/operations.md` | 運用・障害対応 |

最終更新: 2026-06-04
