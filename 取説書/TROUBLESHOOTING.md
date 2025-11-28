# OITERU トラブルシューティングガイド

このドキュメントは、OITERUシステムでよく発生する問題と解決方法をまとめたものです。

---

## 📋 目次

1. [NFCカードリーダーの問題](#1-nfcカードリーダーの問題)
2. [親機(サーバー)の問題](#2-親機サーバーの問題)
3. [子機(Raspberry Pi)の問題](#3-子機raspberry-piの問題)
4. [ネットワークの問題](#4-ネットワークの問題)
5. [データベースの問題](#5-データベースの問題)
6. [Docker関連の問題](#6-docker関連の問題)
7. [ハードウェアの問題](#7-ハードウェアの問題)

---

## 1. NFCカードリーダーの問題

### 問題A: "カードリーダー初期化失敗: No such device"

**症状:**
```
NFCリーダー初期化失敗 (1): [Errno 19] No such device
```

**原因:**
- USBデバイスの物理的な切断
- デバイスドライバーの問題
- 電源供給の不安定さ

**解決方法:**

#### 1. 自動復旧機能を使う(推奨)
```bash
# 最新版は自動リトライ機能付き
sudo python unit_client.py
```

#### 2. ハードウェア確認
```bash
# リーダーが認識されているか確認
lsusb | grep -i sony
# 出力例: Bus 001 Device 005: ID 054c:06c3 Sony Corp.

# nfcpyで確認
python -c "import nfc; print(nfc.ContactlessFrontend('usb'))"
```

#### 3. USB接続の改善
- USBハブを使わず直接接続
- 短い高品質ケーブルに交換
- 別のUSBポートに変更
- 2.5A以上のACアダプタを使用

#### 4. udevルール設定
```bash
sudo nano /etc/udev/rules.d/99-nfc.rules

# 以下を追加
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="06c3", MODE="0666", GROUP="plugdev"

# 適用
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 5. systemdサービス化(自動再起動)
```bash
# サービスファイルをコピー
sudo cp oiteru-unit.service /etc/systemd/system/

# パスを編集
sudo nano /etc/systemd/system/oiteru-unit.service

# 有効化
sudo systemctl daemon-reload
sudo systemctl enable oiteru-unit.service
sudo systemctl start oiteru-unit.service

# 状態確認
sudo systemctl status oiteru-unit.service
```

### 問題B: WSL2でUSBリーダーが認識されない

**症状:**
Windowsでは認識されるが、WSL2から見えない

**解決方法:**

#### 1. usbipd-winを使う
```powershell
# Windows(管理者権限)で実行
usbipd list
usbipd bind --busid 1-4
usbipd attach --wsl --busid 1-4
```

#### 2. 自動接続スクリプト
```bash
./scripts/auto_attach_card_reader.sh
```

#### 3. Dockerコンテナに渡す
```yaml
# docker-compose.yml
devices:
  - /dev/bus/usb:/dev/bus/usb
volumes:
  - /run/pcscd/pcscd.comm:/run/pcscd/pcscd.comm
```

### 問題C: Permission denied

**症状:**
```
PermissionError: [Errno 13] Permission denied: '/dev/bus/usb/001/005'
```

**解決方法:**
```bash
# sudoで実行
sudo python unit_client.py

# またはユーザーをグループに追加
sudo usermod -a -G dialout $USER
sudo usermod -a -G plugdev $USER

# 再ログイン後に有効
```

---

## 2. 親機(サーバー)の問題

### 問題A: Dockerコンテナが起動しない

**確認方法:**
```bash
docker-compose -f docker-compose.mysql.yml ps
docker-compose logs
```

**よくある原因:**

#### ポートが既に使用されている
```bash
# ポート使用状況確認
sudo lsof -i :5000
sudo lsof -i :3306

# プロセスを停止
sudo kill -9 <PID>
```

#### Dockerボリュームの問題
```bash
# ボリュームを削除して再作成
docker-compose down -v
docker-compose up -d
```

### 問題B: 管理画面にアクセスできない

**確認:**
```bash
# コンテナが動いているか
docker ps | grep oiteru

# ログ確認
docker logs oiteru_flask
```

**解決方法:**
1. `http://localhost:5000` でアクセス
2. ファイアウォール確認
3. Dockerを再起動

### 問題C: データベースに接続できない

**MySQL接続確認:**
```bash
# コンテナ内から接続テスト
docker exec -it oiteru_flask mysql \
  -h mysql \
  -u oiteru_user \
  -poiteru_password_2025 \
  -e "SHOW DATABASES;"
```

**解決方法:**
1. MySQL環境変数を確認
2. MySQLコンテナのログ確認: `docker logs oiteru_mysql`
3. ネットワーク確認: `docker network ls`

---

## 3. 子機(Raspberry Pi)の問題

### 問題A: 親機に接続できない

**確認:**
```bash
# 親機にpingが通るか
ping <親機IP>

# ポートが開いているか
telnet <親機IP> 5000

# Tailscale接続確認
tailscale status
```

**解決方法:**

#### Tailscale未接続
```bash
sudo tailscale up
tailscale ip -4  # IPアドレス確認
```

#### 設定ファイル確認
```bash
# config.jsonを確認
cat config.json | grep SERVER_URL

# GUIで設定
sudo python unit_client.py
```

### 問題B: モーターが動かない

**確認:**
```bash
# GPIO権限
sudo python -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('OK')"

# I2C確認(PCA9685使用時)
sudo i2cdetect -y 1
```

**解決方法:**
1. `sudo`で実行
2. 配線を確認
3. 電源供給を確認(5V/3A推奨)

### 問題C: センサーが反応しない

**テストモード:**
```bash
# センサー単体テスト
sudo python test_sensor.py

# unit_client統合テスト
sudo python unit_client.py --test-sensor
```

**確認項目:**
1. GPIO 22に正しく配線されているか
2. プルアップ抵抗が有効か(`GPIO.PUD_UP`)
3. センサー電源(VCC, GND)が接続されているか

---

## 4. ネットワークの問題

### 問題A: Tailscaleで接続できない

**確認:**
```bash
# 接続状態
tailscale status

# IPアドレス
tailscale ip -4
```

**解決方法:**
```bash
# 再ログイン
sudo tailscale down
sudo tailscale up

# ファイアウォール確認
sudo ufw allow from 100.0.0.0/8
```

### 問題B: ローカルネットワークで見つからない

**親機探知:**
```bash
# 子機側で自動探知
sudo python unit_client.py --find-server
```

**手動設定:**
```bash
# 親機のIPを調べる
ip addr show

# config.jsonに設定
{
  "SERVER_URL": "http://192.168.1.100:5000"
}
```

---

## 5. データベースの問題

### 問題A: データが保存されない

**原因:**
- トランザクションのコミット忘れ
- 権限不足
- ディスク容量不足

**確認:**
```bash
# MySQLログ確認
docker logs oiteru_mysql

# ディスク容量
df -h
```

**解決方法:**
```python
# db_adapter.pyでcommitを確認
with get_connection() as conn:
    db.execute(conn, "INSERT ...")
    # conn.commit() が自動実行される
```

### 問題B: データベースが破損

**バックアップから復元:**
```bash
# 最新バックアップを探す
ls -lt *.sql

# 復元
docker exec -i oiteru_mysql mysql \
  -u root -poiteru_root_password_2025 \
  oiteru < backup.sql
```

### 問題C: 複数親機でデータが同期されない

**確認:**
```bash
# 各親機で同じデータベースを見ているか確認
docker exec oiteru_flask env | grep MYSQL_HOST

# 接続テスト
docker exec oiteru_flask mysql -h <MYSQL_HOST> -u oiteru_user -p -e "SELECT COUNT(*) FROM users;"
```

---

## 6. Docker関連の問題

### 問題A: イメージのビルドに失敗

**解決方法:**
```bash
# キャッシュをクリア
docker system prune -a

# 再ビルド
docker-compose build --no-cache
```

### 問題B: ボリュームが残っている

**クリーンアップ:**
```bash
# 停止
docker-compose down

# ボリューム削除
docker volume rm $(docker volume ls -q | grep oiteru)

# 再起動
docker-compose up -d
```

### 問題C: ログが大きくなりすぎる

**ログローテーション設定:**
```yaml
# docker-compose.yml
services:
  flask:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 7. ハードウェアの問題

### 問題A: モーターが動くが排出されない

**確認項目:**
1. モーター速度: `MOTOR_SPEED` を上げる
2. 回転時間: `MOTOR_DURATION` を延ばす
3. 回転方向: `MOTOR_REVERSE` を変更
4. 機械的な詰まり: 手動で回して確認

**設定例:**
```json
{
  "MOTOR_SPEED": 100,
  "MOTOR_DURATION": 3.0,
  "MOTOR_REVERSE": true
}
```

### 問題B: LEDが点灯しない

**確認:**
```bash
# GPIOテスト
sudo python -c "
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, GPIO.HIGH)
import time; time.sleep(2)
GPIO.cleanup()
"
```

**原因:**
- ピン番号が間違っている
- LEDの極性が逆
- 抵抗値が大きすぎる

### 問題C: 電源が不安定

**症状:**
- Raspberry Piが勝手に再起動
- USBデバイスが切断される
- モーターが動かない

**解決方法:**
1. 3A以上の電源アダプタを使用
2. USBハブに電源供給
3. モーター用に外部電源を用意

---

## 🆘 それでも解決しない場合

### システム診断を実行

```bash
# 親機診断
python diagnostics.py

# 子機診断(自動実行)
sudo python unit_client.py
```

### ログを収集

```bash
# 親機ログ
docker-compose logs > server_logs.txt

# 子機ログ
sudo journalctl -u oiteru-unit.service > unit_logs.txt
```

### データをエクスポート

```bash
# 全データをExcel出力
python data_viewer.py export-all
```

### クリーンインストール

```bash
# 全て削除して最初から
docker-compose down -v
git pull
docker-compose up --build -d
```

---

## 📞 サポート

問題が解決しない場合:
1. システム診断を実行
2. ログを確認
3. GitHub Issuesで報告(ログを添付)

---

## 📚 関連ドキュメント

- [README.md](README.md) - 基本ガイド
- [ADVANCED.md](ADVANCED.md) - 上級者向けガイド

---

**最終更新: 2025年11月28日**
