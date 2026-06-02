# OITERU クイック起動メモ

詳しい手順は `取説書/QUICKSTART.md` にまとめています。このファイルは、すでに概要を知っている人向けの短いメモです。

標準は **Linux 系 OS + tmux + MySQL + db_server.py + unit.py** です。

## 1. 親機

```bash
cd ~/Desktop/oiteru_202603
git pull

# 初回だけ
cp .env.example .env
nano .env

docker compose -f docker-compose.mysql.yml up -d

tmux new -s oiteru-parent
./venv-start.sh parent-mysql
```

管理画面:

```text
http://<親機IP>:5000/admin
```

## 2. 子機

```bash
cd ~/Desktop/oiteru_202603
git pull

# 初回だけ
cp config.example.json config.json
nano config.json

sudo apt update
sudo apt install -y pigpio tmux python3-full python3-venv python3-pip
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

tmux new -s oiteru-unit
./venv-start.sh unit
```

子機 CUI で最初に確認する項目:

| メニュー | 内容 |
|---|---|
| `22` | 自動選択正方向テスト |
| `23` | 自動選択逆方向テスト |
| `26` | GPIO フォールバック強制テスト |
| `off` | コイル OFF |
| `s` | 設定保存して起動 |

## 3. tmux 操作

| やりたいこと | コマンド |
|---|---|
| 一時退出 | `Ctrl+b` → `d` |
| 一覧 | `tmux ls` |
| 親機に戻る | `tmux attach -t oiteru-parent` |
| 子機に戻る | `tmux attach -t oiteru-unit` |
| セッション削除 | `tmux kill-session -t <名前>` |

## 4. よく使う確認

```bash
git branch --show-current
git status --short
docker compose -f docker-compose.mysql.yml ps
systemctl status pigpiod
python -m unittest tests.test_stepper_driver
```

## 5. 詳細資料

| ファイル | 内容 |
|---|---|
| `README.md` | 全体像 |
| `取説書/QUICKSTART.md` | 初心者向けの詳細起動手順 |
| `取説書/README.md` | 取説書の目次 |
| `docs/operations.md` | 運用・障害対応 |

最終更新: 2026-06-02
