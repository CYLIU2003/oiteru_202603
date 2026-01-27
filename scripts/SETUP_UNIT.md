# 子機環境セットアップガイド

このガイドでは、Raspberry Pi上でOITERU子機を動作させるための環境準備手順を説明します。

## 📋 前提条件

- Raspberry Pi 3/4/5 (Raspberry Pi OS Bullseye以降)
- インターネット接続
- 管理者権限 (sudo)

## 🚀 クイックセットアップ

### 方法1: 自動セットアップスクリプト (推奨)

```bash
# プロジェクトディレクトリに移動
cd ~/oiteru_250827_restAPI

# セットアップスクリプトを実行
chmod +x scripts/setup_unit_environment.sh
./scripts/setup_unit_environment.sh
```

スクリプトが以下を自動で実行します:
1. システムパッケージの更新
2. 必要なライブラリのインストール
3. I2Cインターフェースの有効化
4. Python仮想環境の作成
5. Pythonパッケージのインストール
6. 設定ファイルのテンプレート作成

### 方法2: 手動セットアップ

#### 1. システムパッケージのインストール

```bash
# システム更新
sudo apt-get update
sudo apt-get upgrade -y

# 必要なパッケージをインストール
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-tk \
    libusb-1.0-0-dev \
    libnfc-dev \
    pcscd \
    i2c-tools \
    git \
    tmux
```

#### 2. I2Cの有効化

```bash
# raspi-configを起動
sudo raspi-config

# 以下の順で選択:
# 3. Interface Options
# → I5 I2C
# → Yes

# 再起動
sudo reboot
```

または、手動で設定:

```bash
# config.txtを編集
sudo nano /boot/firmware/config.txt  # Bookworm以降
# または
sudo nano /boot/config.txt  # 旧バージョン

# 以下を追加
dtparam=i2c_arm=on

# モジュールを自動読み込み
echo "i2c-dev" | sudo tee -a /etc/modules

# ユーザーをi2cグループに追加
sudo usermod -aG i2c $USER

# 再起動
sudo reboot
```

#### 3. Python仮想環境の作成

```bash
cd ~/oiteru_250827_restAPI

# 仮想環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate
```

#### 4. Pythonパッケージのインストール

```bash
# pipを最新版に更新
pip install --upgrade pip setuptools wheel

# 子機用パッケージをインストール
pip install -r docker/requirements-client.txt
```

### インストールされるパッケージ

- **requests** (>=2.28.0) - HTTP通信
- **flask** (>=3.0.0) - リモート設定変更受信用APIサーバー
- **psutil** (>=5.9.0) - CPU/メモリ使用率取得
- **nfcpy** (>=1.0.4) - NFCカードリーダー制御
- **RPi.GPIO** (>=0.7.1) - GPIO制御
- **Adafruit-PCA9685** (>=1.0.1) - サーボモーター制御
- **pyserial** (>=3.5) - Arduino通信

## ⚙️ 設定

### config.jsonの作成

```bash
# テンプレートをコピー
cp config_templates/config_unit.template.json config.json

# 設定ファイルを編集
nano config.json
```

### 必須設定項目

```json
{
  "SERVER_URL": "http://100.114.99.67:5000",  // 親機のURL
  "UNIT_NAME": "2号機",                        // この子機の名前
  "UNIT_PASSWORD": "password123",              // この子機のパスワード
  "MOTOR_TYPE": "SERVO",                       // SERVO or STEPPER
  "CONTROL_METHOD": "RASPI_DIRECT"             // RASPI_DIRECT or ARDUINO_SERIAL
}
```

## 🏃 起動

### 通常起動

```bash
# 仮想環境を有効化
source venv/bin/activate

# 子機を起動
python unit.py
```

### tmuxセッションで起動 (推奨)

tmuxを使用すると、SSH接続を切断してもプロセスが継続します。

```bash
# tmuxセッションを作成して起動
tmux new-session -d -s oiteru 'source venv/bin/activate && python unit.py'

# ログを確認
tmux attach -t oiteru

# セッションから切り離し (Ctrl+B → D)

# セッション一覧
tmux ls

# セッション終了
tmux kill-session -t oiteru
```

### systemdサービスとして起動 (自動起動)

```bash
# サービスファイルを作成
sudo nano /etc/systemd/system/oiteru-unit.service
```

```ini
[Unit]
Description=OITERU Unit Client
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/oiteru_250827_restAPI
ExecStart=/home/pi/oiteru_250827_restAPI/venv/bin/python unit.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# サービスを有効化
sudo systemctl daemon-reload
sudo systemctl enable oiteru-unit
sudo systemctl start oiteru-unit

# ステータス確認
sudo systemctl status oiteru-unit

# ログ確認
sudo journalctl -u oiteru-unit -f
```

## 🔧 トラブルシューティング

### NFCリーダーが認識されない

```bash
# USBデバイスを確認
lsusb | grep -i sony

# 期待される出力:
# Bus 001 Device 004: ID 054c:06c3 Sony Corp. RC-S380

# pcscdサービスを再起動
sudo systemctl restart pcscd
sudo systemctl status pcscd
```

### I2Cが動作しない

```bash
# I2Cデバイスをスキャン
sudo i2cdetect -y 1

# PCA9685が接続されている場合、0x40にデバイスが表示される
```

### psutilが動作しない

```bash
# 仮想環境内で再インストール
source venv/bin/activate
pip uninstall psutil
pip install psutil
```

### GPIO権限エラー

```bash
# ユーザーをgpioグループに追加
sudo usermod -aG gpio $USER

# 再ログイン
exit
```

## 📊 動作確認

### システム情報の確認

親機の管理画面から「デバッグ・診断」セクションで以下を実行:
- **接続テスト**: 子機との通信確認
- **ステータス取得**: CPU/メモリ使用率などを表示

### ログの確認

```bash
# tmuxセッションのログを確認
tmux attach -t oiteru

# systemdサービスのログを確認
sudo journalctl -u oiteru-unit -n 100 --no-pager
```

## 🆘 サポート

問題が発生した場合:
1. ログを確認する (tmuxまたはjournalctl)
2. config.jsonの設定を確認する
3. ネットワーク接続を確認する (親機にpingが通るか)
4. GitHubのIssuesで報告する

## 📚 関連ドキュメント

- [QUICKSTART.md](../取説書/QUICKSTART.md) - 全体的なクイックスタートガイド
- [config_templates/README.md](../config_templates/README.md) - 設定ファイルの詳細
