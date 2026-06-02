# OITERU システム

OITERU は、NFC カードをかざすと生理用品を排出し、利用履歴・在庫・子機状態を管理する IoT システムです。

このリポジトリでは、親機と子機を **Linux 系 OS 上で tmux 経由で起動する運用**を標準にします。Windows 用スクリプトや legacy 経路は残っていますが、初めて触る人はこの README と `取説書/QUICKSTART.md` の Linux/tmux 手順を優先してください。

## まず読む順番

| 順番 | ファイル | 目的 |
|---:|---|---|
| 1 | `README.md` | 全体像と最短起動だけ確認する |
| 2 | `取説書/QUICKSTART.md` | 初心者向けに親機・子機を実際に起動する |
| 3 | `取説書/README.md` | 取説書フォルダの目次を見る |
| 4 | `docs/operations.md` | 日常運用・障害対応・引き継ぎを見る |

## 標準構成

| 項目 | 標準 |
|---|---|
| 親機 OS | Linux 系 OS |
| 子機 OS | Raspberry Pi OS / Linux 系 OS |
| 起動方法 | `tmux` 経由 |
| 親機エントリポイント | `db_server.py` |
| 子機エントリポイント | `unit.py` |
| DB | MySQL 8 (InnoDB) |
| 親機 DB 起動 | `docker compose -f docker-compose.mysql.yml up -d` |
| 子機モーター | 28BYJ-48 + ULN2003AN |
| 子機モーターバックエンド | PigpioZero → RpiMotorLib → GPIO fallback |

`server.py + SQLite` は legacy 互換経路です。新規セットアップ、実証運用、レビューでは使わないでください。

## システムの役割

| 名前 | 役割 | 起動するもの |
|---|---|---|
| 親機 | 管理画面、DB、利用履歴、子機状態管理 | MySQL + `db_server.py` |
| 子機 | NFC 読み取り、排出制御、heartbeat 送信 | `unit.py` |
| 従親機 | 必要な場合だけ使うサブサーバー | 親機 DB に接続するサーバー |

## 最短起動: 親機 Linux/tmux

```bash
cd ~/Desktop/oiteru_202603
git pull

# 初回だけ
cp .env.example .env
nano .env

# MySQL を Docker で起動
docker compose -f docker-compose.mysql.yml up -d

# tmux で親機を起動
tmux new -s oiteru-parent
./venv-start.sh parent-mysql
```

`.env` では最低限、次を変更してください。

| 変数 | 内容 |
|---|---|
| `FLASK_SECRET_KEY` | Flask セッション用の長いランダム文字列 |
| `OITERU_ADMIN_PASSWORD` | 管理画面ログイン用パスワード |
| `MYSQL_PASSWORD` | MySQL 接続パスワード |
| `MYSQL_ROOT_PASSWORD` | MySQL root パスワード |

tmux から一時退出するには `Ctrl+b` の後に `d` を押します。

戻るには:

```bash
tmux attach -t oiteru-parent
```

## 最短起動: 子機 Raspberry Pi/Linux/tmux

```bash
cd ~/Desktop/oiteru_202603
git pull

# 初回だけ
cp config.example.json config.json
nano config.json

# PigpioZero バックエンド用。初回だけ enable、毎回 start しても問題ありません。
sudo apt update
sudo apt install -y pigpio tmux python3-full python3-venv python3-pip
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# tmux で子機を起動
tmux new -s oiteru-unit
./venv-start.sh unit
```

`config.json` では最低限、次を子機ごとに変更してください。

| キー | 内容 | 例 |
|---|---|---|
| `SERVER_URL` | 親機 URL | `http://192.168.1.10:5000` |
| `UNIT_NAME` | 管理画面に出る子機名 | `unit-01` |
| `UNIT_PASSWORD` | 親機と合わせる子機パスワード | `change-this` |

戻るには:

```bash
tmux attach -t oiteru-unit
```

## tmux の最低限

| やりたいこと | コマンド |
|---|---|
| 新しいセッションを作る | `tmux new -s oiteru-parent` |
| セッションから抜ける | `Ctrl+b` → `d` |
| セッション一覧を見る | `tmux ls` |
| セッションに戻る | `tmux attach -t oiteru-parent` |
| 起動中アプリを止める | セッション内で `Ctrl+c` |
| セッションを消す | `tmux kill-session -t oiteru-parent` |

## 子機モーター設定

現在のブランチでは、28BYJ-48 + ULN2003AN を次の順で制御します。

| 優先 | バックエンド | 内容 |
|---:|---|---|
| 1 | PigpioZero | `gpiozero` + `pigpio`。実機動作済みの `stepping_movement.py` を統合した経路 |
| 2 | RpiMotorLib | `RpiMotorLib.BYJMotor` による制御 |
| 3 | GPIO fallback | RPi.GPIO 直制御のフォールバック |

既定の配線は BCM 番号です。物理ピン番号ではありません。

| ULN2003AN | Raspberry Pi BCM |
|---|---:|
| IN1 | GPIO21 |
| IN2 | GPIO17 |
| IN3 | GPIO27 |
| IN4 | GPIO22 |

この既定値は、実機動作済みの `stepping_movement.py` と同じです。LED やセンサーを使う場合は、同じ GPIO を兼用しないでください。`config.example.json` では LED/センサーを GPIO5/6/13 に逃がしています。

CUI から確認する順番:

```text
22. 自動選択正方向テスト
23. 自動選択逆方向テスト
26. GPIOフォールバック強制
off. コイルOFF
s. 保存して起動
```

正常時のログ例:

```text
[STEPPER] backend=PigpioZero pins(IN1-4)=[21, 17, 27, 22] ...
[STEPPER] start (nfc-dispense)
[STEPPER] done (nfc-dispense)
[STEPPER] coils off
```

## よく使う確認コマンド

```bash
# ブランチ確認
git branch --show-current

# tmux確認
tmux ls

# 親機が開いているか
curl http://localhost:5000

# MySQLコンテナ確認
docker compose -f docker-compose.mysql.yml ps

# pigpio確認
systemctl status pigpiod

# Pythonテスト
python -m unittest tests.test_stepper_driver
```

## ディレクトリ概要

```text
oiteru_202603/
├── db_server.py              # 標準の親機エントリポイント(MySQL)
├── unit.py                   # 子機エントリポイント
├── stepper_driver.py         # 28BYJ-48 + ULN2003AN 制御バックエンド
├── stepping_patch.py         # main_stepping_branch 用 runtime patch
├── config.example.json       # 子機 config.json のテンプレート
├── .env.example              # 親機 .env のテンプレート
├── docker-compose.mysql.yml  # MySQL 標準構成
├── requirements-client.txt   # 子機依存パッケージ
├── tests/                    # 単体テスト
├── docs/                     # 運用資料
└── 取説書/                   # 初心者向け手順書
```

## Git 管理しないもの

次のファイルは秘密情報やローカル状態を含むため、コミットしないでください。

| ファイル | 理由 |
|---|---|
| `.env` | 管理者パスワード、DB パスワード |
| `config.json` | 子機パスワード、設置場所、親機 URL |
| `*.log` | 運用ログ |
| `*.sqlite3` | legacy DB / ローカルデータ |

## 次に読む

実際の作業手順は `取説書/QUICKSTART.md` に詳しくまとめています。

```bash
less 取説書/QUICKSTART.md
```

最終更新: 2026-06-02
