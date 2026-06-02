# OITERU かんたんスタートガイド

このガイドは、OITERU を初めて触る人が **Linux 系 OS + tmux** で親機と子機を起動できるようにまとめた手順書です。

コマンドを上から順に実行すれば、基本的な起動確認まで進められるようにしています。

## 0. 最初に知っておくこと

### 役割

| 名前 | 何をするか | 主なファイル |
|---|---|---|
| 親機 | 管理画面、DB、利用履歴、子機状態を管理する | `db_server.py` |
| 子機 | NFC カードを読み、モーターで排出する | `unit.py` |
| 従親機 | 親機 DB を参照する追加サーバー。必要な時だけ使う | `server.py` など |

### 標準構成

| 項目 | 標準 |
|---|---|
| OS | Linux 系 OS |
| 起動方法 | tmux |
| DB | MySQL 8 (InnoDB) |
| 親機 | `db_server.py` |
| 子機 | `unit.py` |
| 子機モーター | 28BYJ-48 + ULN2003AN |

SQLite と `server.py` は legacy 経路です。新しく作業する人は使わないでください。

## 1. tmux の超基本

tmux は、SSH を切ってもプログラムを動かし続けるための道具です。

| やりたいこと | コマンド |
|---|---|
| セッションを作る | `tmux new -s oiteru-parent` |
| 画面から一時退出する | `Ctrl+b` → `d` |
| セッション一覧を見る | `tmux ls` |
| セッションに戻る | `tmux attach -t oiteru-parent` |
| アプリを止める | セッション内で `Ctrl+c` |
| セッションを削除する | `tmux kill-session -t oiteru-parent` |

名前は分かりやすくしてください。

| 用途 | 推奨セッション名 |
|---|---|
| 親機 | `oiteru-parent` |
| 子機 | `oiteru-unit` |
| 従親機 | `oiteru-sub-parent` |

## 2. 共通準備

親機でも子機でも、まずプロジェクトフォルダへ移動します。

```bash
cd ~/Desktop/oiteru_202603
```

場所が分からない場合:

```bash
find ~ -name unit.py 2>/dev/null | grep oiteru
```

現在の場所を確認:

```bash
pwd
```

ブランチ確認と最新化:

```bash
git branch --show-current
git pull
git status --short
```

必要な Linux パッケージ:

```bash
sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip curl
```

Docker を親機で使う場合は Docker も必要です。

```bash
docker --version
docker compose version
```

Docker が無い場合は、先に Docker を入れてから親機を起動してください。

## 3. 親機の初回設定

親機では `.env` を作ります。

```bash
cp .env.example .env
nano .env
```

最低限、次を変更してください。

| 変数 | 何を入れるか |
|---|---|
| `FLASK_SECRET_KEY` | 長いランダム文字列 |
| `OITERU_ADMIN_PASSWORD` | 管理画面ログイン用パスワード |
| `MYSQL_PASSWORD` | MySQL 接続パスワード |
| `MYSQL_ROOT_PASSWORD` | MySQL root パスワード |

保存方法:

```text
Ctrl+o → Enter → Ctrl+x
```

## 4. 親機を tmux で起動する

MySQL を Docker で起動します。

```bash
docker compose -f docker-compose.mysql.yml up -d
```

状態確認:

```bash
docker compose -f docker-compose.mysql.yml ps
```

親機用 tmux を作ります。

```bash
tmux new -s oiteru-parent
```

tmux の中で親機を起動します。

```bash
cd ~/Desktop/oiteru_202603
./venv-start.sh parent-mysql
```

起動後、ブラウザで開きます。

```text
http://<親機IP>:5000/admin
```

同じ PC で確認する場合:

```text
http://localhost:5000/admin
```

SSH から抜けたい場合は `Ctrl+b` → `d` です。親機は動き続けます。

親機へ戻る:

```bash
tmux attach -t oiteru-parent
```

## 5. 子機の初回設定

子機では `config.json` を作ります。

```bash
cd ~/Desktop/oiteru_202603
cp config.example.json config.json
nano config.json
```

最低限、次を変更してください。

| キー | 何を入れるか | 例 |
|---|---|---|
| `SERVER_URL` | 親機 URL | `http://192.168.1.10:5000` |
| `UNIT_NAME` | 子機名 | `unit-01` |
| `UNIT_PASSWORD` | 親機と合わせる子機パスワード | `change-this` |

モーター設定の基本:

| キー | 推奨値 | 説明 |
|---|---|---|
| `MOTOR_TYPE` | `STEPPER` | ステッピングモーター |
| `CONTROL_METHOD` | `RASPI_DIRECT` | Raspberry Pi GPIO 直結 |
| `STEPPER_BACKEND` | `auto` | PigpioZero → RpiMotorLib → GPIO の順で自動選択 |
| `STEPPER_PINS` | `[5, 6, 13, 19]` | BCM 番号。物理ピン番号ではない |
| `STEPPER_DRIVE_MODE` | `full` | 最初はトルクが出やすい full 推奨 |
| `STEPPER_STEP_DELAY` | `0.01` | 速すぎると脱調する |

保存方法:

```text
Ctrl+o → Enter → Ctrl+x
```

## 6. 子機のハードウェア準備

子機では pigpio を有効にします。

```bash
sudo apt update
sudo apt install -y pigpio tmux python3-full python3-venv python3-pip
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
systemctl status pigpiod
```

ステッピングモーターの既定配線は BCM 番号です。

| ULN2003AN | Raspberry Pi BCM |
|---|---:|
| IN1 | GPIO5 |
| IN2 | GPIO6 |
| IN3 | GPIO13 |
| IN4 | GPIO19 |

重要:

| 確認 | 内容 |
|---|---|
| 電源 | 28BYJ-48 は 5V 電源が必要 |
| GND | Raspberry Pi と外部電源の GND を共通にする |
| 番号 | `STEPPER_PINS` は BCM 番号 |
| pigpio | `systemctl status pigpiod` が active |

## 7. 子機を tmux で起動する

子機用 tmux を作ります。

```bash
tmux new -s oiteru-unit
```

tmux の中で子機を起動します。

```bash
cd ~/Desktop/oiteru_202603
./venv-start.sh unit
```

CUI メニューが出たら、まずモーターだけ確認します。

| メニュー | 内容 |
|---|---|
| `22` | 自動選択正方向テスト |
| `23` | 自動選択逆方向テスト |
| `26` | GPIO フォールバック強制テスト |
| `off` | コイル OFF |
| `s` | 設定保存して起動 |
| `q` | 保存せず起動 |

期待ログ:

```text
[STEPPER] backend=PigpioZero pins(IN1-4)=[5, 6, 13, 19] ...
[STEPPER] start (...)
[STEPPER] done (...)
[STEPPER] coils off
```

SSH から抜けたい場合は `Ctrl+b` → `d` です。子機は動き続けます。

子機へ戻る:

```bash
tmux attach -t oiteru-unit
```

## 8. NFC 排出確認

子機が起動したら、カードをかざして排出処理を確認します。

確認するログ:

```text
[DEBUG] dispense_item: MOTOR_REVERSE=False, SPEED=..., DURATION=...
[STEPPER] backend=PigpioZero
[STEPPER] start (nfc-dispense)
[STEPPER] done (nfc-dispense)
```

次のログが出る場合は分岐注入が失敗しています。

```text
!! 未サポートのモーター設定です: STEPPER, RASPI_DIRECT
```

その場合は以下を実行して確認します。

```bash
python - <<'PY'
from pathlib import Path
from stepping_patch import patch_unit_client_source

src = Path('archive/unit_client.py').read_text(encoding='utf-8')
patched = patch_unit_client_source(src)
marker = "elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':"
print('marker_present =', marker in patched)
PY
```

`marker_present = True` が正常です。

## 9. 日常運用

### 親機へ戻る

```bash
tmux attach -t oiteru-parent
```

### 子機へ戻る

```bash
tmux attach -t oiteru-unit
```

### tmux 一覧

```bash
tmux ls
```

### 親機停止

```bash
tmux attach -t oiteru-parent
# セッション内で
Ctrl+c
exit
```

### 子機停止

```bash
tmux attach -t oiteru-unit
# セッション内で
Ctrl+c
exit
```

### MySQL 停止

```bash
docker compose -f docker-compose.mysql.yml down
```

### MySQL は残して親機だけ再起動

```bash
tmux attach -t oiteru-parent
Ctrl+c
./venv-start.sh parent-mysql
```

### 子機だけ再起動

```bash
tmux attach -t oiteru-unit
Ctrl+c
./venv-start.sh unit
```

## 10. よくあるトラブル

### tmux duplicate session と出る

すでに同じ名前の tmux があります。

戻る:

```bash
tmux attach -t oiteru-unit
```

不要なら消す:

```bash
tmux kill-session -t oiteru-unit
tmux new -s oiteru-unit
```

### tmux から抜け方が分からない

`Ctrl+b` を押してから `d` です。同時押しではありません。

### 管理画面にアクセスできない

親機側で確認:

```bash
tmux attach -t oiteru-parent
docker compose -f docker-compose.mysql.yml ps
curl http://localhost:5000
```

別 PC から見る場合は、親機 IP とポート 5000 が正しいか確認してください。

### MySQL が起動しない

```bash
docker compose -f docker-compose.mysql.yml ps
docker compose -f docker-compose.mysql.yml logs mysql
```

`.env` の `MYSQL_*` が変更済みか確認してください。

### 子機が親機に接続できない

子機側で確認:

```bash
curl http://<親機IP>:5000
```

`config.json` の `SERVER_URL` が `http://<親機IP>:5000` になっているか確認してください。

### pigpio が使えない

```bash
sudo systemctl start pigpiod
systemctl status pigpiod
```

それでも動かない場合は、子機 CUI の `26` で GPIO fallback を確認してください。

### モーターが回らない

順番に確認してください。

| 確認 | 内容 |
|---|---|
| CUI | `22` と `23` を実行したか |
| backend | ログに `backend=PigpioZero` または `backend=RpiMotorLib` が出るか |
| 配線 | `STEPPER_PINS` が実際の BCM 番号と一致するか |
| 電源 | ULN2003AN に 5V が来ているか |
| GND | Raspberry Pi と外部電源の GND が共通か |
| LED | ULN2003 基板の LED が点滅するか |
| 速度 | `STEPPER_STEP_DELAY` を `0.02` や `0.03` にする |
| 順番 | CUI の配線順スキャンを試す |

### NFC が読めない

```bash
lsusb
python - <<'PY'
import nfc
print(nfc)
PY
```

USB リーダーを抜き差しし、子機を再起動してください。

### externally-managed-environment と出る

Raspberry Pi OS Bookworm 以降では、直接 `pip install` しないで venv を使います。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-client.txt
```

通常は `./venv-start.sh unit` が自動で処理します。

## 11. 補足: systemd 化

tmux は手作業・デバッグ向けです。実証で常時運用する段階では systemd 化を検討してください。

子機 systemd 例:

```ini
[Unit]
Description=OITERU Unit Client
After=network-online.target pigpiod.service
Wants=network-online.target pigpiod.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Desktop/oiteru_202603
ExecStart=/bin/bash /home/pi/Desktop/oiteru_202603/venv-start.sh unit
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

パスと `User` は実機に合わせて変更してください。

## 12. 補足: Windows について

Windows 用の PowerShell や bat スクリプトは残っていますが、この取説の標準ではありません。

レビュー、実証運用、引き継ぎでは Linux/tmux 手順を基準にしてください。

## 13. 作業前後チェックリスト

作業前:

```bash
git branch --show-current
git pull
git status --short
tmux ls
```

作業後:

```bash
python -m unittest tests.test_stepper_driver
docker compose -f docker-compose.mysql.yml ps
systemctl status pigpiod
```

秘密情報確認:

```bash
git status --short
```

`.env`, `config.json`, ログ、DB ファイルをコミットしないでください。

最終更新: 2026-06-02
