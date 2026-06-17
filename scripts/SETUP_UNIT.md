# 子機環境セットアップガイド

このガイドでは、Raspberry Pi 上で OITERU 子機を tmux で動かすための環境準備を説明します。

標準は **Linux 系 OS + tmux + `unit.py`** です。古い Docker や systemd 前提の手順は、この資料では扱いません。

## 前提条件

- Raspberry Pi 3/4/5
- Raspberry Pi OS Bullseye 以降
- インターネット接続
- 管理者権限
- 親機の URL が分かっていること

## 自動セットアップ

```bash
cd ~/Desktop/oiteru_202603
chmod +x scripts/setup_unit_environment.sh
./scripts/setup_unit_environment.sh
```

セットアップ後、`config.json` を確認します。

```bash
cp config.example.json config.json
nano config.json
```

最低限、次を変更してください。

| キー | 内容 | 例 |
|---|---|---|
| `SERVER_URL` | 親機 URL | `http://192.168.1.10:5000` |
| `UNIT_NAME` | 子機名 | `unit-01` |
| `UNIT_PASSWORD` | 親機側と合わせるパスワード | `change-this` |
| `MOTOR_TYPE` | `SERVO` または `STEPPER` | `STEPPER` |
| `CONTROL_METHOD` | ラズパイ直結なら `RASPI_DIRECT` | `RASPI_DIRECT` |
| `STEPPER_BACKEND` | ステッパー制御方式 | `auto` |

## 手動セットアップ

```bash
sudo apt update
sudo apt install -y \
    git \
    tmux \
    curl \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-tk \
    libusb-1.0-0-dev \
    libnfc-dev \
    pcscd \
    pcsc-tools \
    i2c-tools
```

Python 仮想環境:

```bash
cd ~/Desktop/oiteru_202603
python3 -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r requirements-client.txt
```

I2C を使う構成の場合:

```bash
sudo raspi-config
```

次の順で選択します。

```text
3. Interface Options
I5 I2C
Yes
```

設定後に再起動してください。

```bash
sudo reboot
```

## 起動

```bash
cd ~/Desktop/oiteru_202603
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

tmux から一時退出:

```text
Ctrl+b → d
```

戻る:

```bash
scripts/tmux_oiteru.sh attach unit
```

状態確認:

```bash
scripts/tmux_oiteru.sh status unit
scripts/tmux_oiteru.sh logs unit
```

停止:

```bash
scripts/tmux_oiteru.sh stop unit
```

## NFC リーダー確認

```bash
lsusb
systemctl status pcscd
```

Sony RC-S380 などの USB リーダーを使う場合、認識しないときは抜き差ししてから `pcscd` を再起動します。

```bash
sudo systemctl restart pcscd
```

## GPIO 権限

GPIO 権限エラーが出る場合:

```bash
sudo usermod -aG gpio $USER
```

いったんログアウトしてから入り直してください。

## 親機との接続確認

```bash
curl http://<親機IP>:5000
```

接続できない場合は、`config.json` の `SERVER_URL`、ネットワーク、Tailscale/LAN、親機 tmux の状態を確認してください。

## 作業後チェック

```bash
git status --short
scripts/tmux_oiteru.sh status unit
```

`.env`, `config.json`, `logs/`, ログ、DB ファイルをコミットしないでください。

## 関連ドキュメント

| ファイル | 内容 |
|---|---|
| `../取説書/QUICKSTART.md` | 全体的なクイックスタート |
| `../docs/onboarding.md` | 新規参加者向け |
| `../docs/operations.md` | 運用・障害対応 |
| `../config_templates/README.md` | 設定ファイルの詳細 |

最終更新: 2026-06-17
