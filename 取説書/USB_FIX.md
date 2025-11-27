# NFCカードリーダー問題の修正ガイド

## 問題: Dockerコンテナ内でカードリーダーが検知されない

### 症状

```bash
$ docker exec oiteru_flask ls -la /dev/bus/usb/
# デバイスが表示されない
```

---

## 原因

Dockerコンテナ起動後にUSBデバイスが接続された、または再接続が必要な状態。

---

## 解決方法

### 方法1: コンテナを再起動（推奨）

```bash
# コンテナを停止
docker-compose down

# USBデバイスが接続されていることを確認
lsusb

# コンテナを再起動
docker-compose up -d

# デバイスが認識されたか確認
docker exec oiteru_flask ls -la /dev/bus/usb/
```

### 方法2: WSL2経由でUSBを再アタッチ（Windows環境）

#### 前提条件
- Windows 11またはWindows 10 (バージョン21H2以降)
- usbipd-winがインストール済み

#### 手順

1. **PowerShellを管理者権限で開く**

2. **接続されているUSBデバイスを確認**
   ```powershell
   usbipd list
   ```

   出力例:
   ```
   BUSID  VID:PID    DEVICE                                              STATE
   1-4    054c:0268  Sony FeliCa Port/PaSoRi                            Not shared
   ```

3. **デバイスをWSL2にアタッチ**
   ```powershell
   usbipd bind --busid 1-4
   usbipd attach --wsl --busid 1-4
   ```

4. **WSL内で確認**
   ```bash
   lsusb
   # Sony FeliCa Port/PaSoRiが表示されればOK
   ```

5. **Dockerコンテナを再起動**
   ```bash
   docker-compose restart
   ```

6. **コンテナ内で確認**
   ```bash
   docker exec oiteru_flask ls -la /dev/bus/usb/
   ```

### 方法3: docker-compose.ymlの設定を確認

`docker-compose.yml`に以下の設定があることを確認:

```yaml
services:
  flask:
    privileged: true
    volumes:
      - /dev/bus/usb:/dev/bus/usb
    devices:
      - /dev/bus/usb
```

設定が不足している場合は追加して再起動:

```bash
docker-compose down
docker-compose up -d
```

---

## 診断コマンド

システム診断でカードリーダーの状態を確認できます:

```bash
# ホスト環境で実行
python diagnostics.py

# またはコンテナ内で実行
docker exec oiteru_flask python diagnostics.py
```

出力例:
```
[  OK  ] NFCリーダー        3個のUSBデバイスを検出
```

または:
```
[WARNING] NFCリーダー        USBデバイスが検出されません
```

---

## 自動起動スクリプト

USBデバイスを自動的にアタッチしてコンテナを起動するスクリプト:

### Windows用 (start_with_usb.ps1)

```powershell
# PowerShell スクリプト（管理者権限で実行）

Write-Host "USBデバイスを確認中..." -ForegroundColor Cyan
usbipd list

# カードリーダーのBUSIDを指定（環境に合わせて変更）
$BUSID = "1-4"

Write-Host "USBデバイスをWSLにアタッチ中..." -ForegroundColor Cyan
usbipd bind --busid $BUSID
usbipd attach --wsl --busid $BUSID

Write-Host "Dockerコンテナを起動中..." -ForegroundColor Cyan
wsl -d Ubuntu -e bash -c "cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI && docker-compose up -d"

Write-Host "完了！" -ForegroundColor Green
Write-Host "管理画面: http://localhost:5000/admin" -ForegroundColor Yellow
```

使い方:
```powershell
# 管理者権限のPowerShellで実行
.\start_with_usb.ps1
```

### Linux/WSL用 (start_with_check.sh)

```bash
#!/bin/bash

echo "USBデバイスを確認中..."
lsusb

echo ""
echo "Dockerコンテナを起動中..."
docker-compose up -d

echo ""
echo "カードリーダーの状態を確認中..."
sleep 3
docker exec oiteru_flask python diagnostics.py | grep "NFCリーダー"

echo ""
echo "完了！"
echo "管理画面: http://localhost:5000/admin"
```

使い方:
```bash
chmod +x start_with_check.sh
./start_with_check.sh
```

---

## トラブルシューティング

### Q1: usbipd コマンドが見つからない

**A:** usbipd-winをインストールしてください。

```powershell
# wingetを使用
winget install usbipd

# または公式サイトからダウンロード
# https://github.com/dorssel/usbipd-win/releases
```

### Q2: "Access is denied" エラー

**A:** PowerShellを管理者権限で実行してください。

### Q3: WSL2にアタッチできない

**A:** WSL2が実行中か確認してください。

```powershell
wsl --list --running
```

実行されていない場合:
```powershell
wsl
```

### Q4: コンテナ再起動後もデバイスが見えない

**A:** 以下を順番に試してください:

1. カードリーダーを抜き差し
2. WSL2を再起動
   ```powershell
   wsl --shutdown
   wsl
   ```
3. Dockerデーモンを再起動
   ```bash
   sudo service docker restart
   ```

### Q5: 診断で "WARNING" が表示される

**A:** 以下を確認:

1. docker-compose.ymlの`privileged: true`設定
2. docker-compose.ymlの`volumes`と`devices`設定
3. カードリーダーの物理的な接続
4. USBポートの動作確認（他のUSBデバイスで試す）

---

## 予防策

### コンテナ起動前にUSBをアタッチ

```bash
# 1. USBデバイスをアタッチ（Windows）
# PowerShellで実行
usbipd attach --wsl --busid 1-4

# 2. デバイスを確認
lsusb

# 3. Dockerコンテナを起動
docker-compose up -d
```

### 起動スクリプトを使用

上記の自動起動スクリプトを使用して、毎回正しい順序で起動。

### Windowsタスクスケジューラで自動起動

1. タスクスケジューラを開く
2. 新しいタスクを作成
3. トリガー: システム起動時
4. 操作: `start_with_usb.ps1`を実行
5. 最高特権で実行にチェック

---

## 関連ドキュメント

- [DIAGNOSTICS.md](DIAGNOSTICS.md) - システム診断機能
- [DOCKER_UNIT.md](DOCKER_UNIT.md) - Docker環境の詳細
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング

---

## まとめ

| 状況 | 解決方法 |
|------|----------|
| **コンテナ起動後にUSB接続** | コンテナ再起動 |
| **Windows環境** | usbipd でUSBをアタッチ |
| **頻繁に問題が発生** | 自動起動スクリプトを使用 |
| **設定を確認したい** | `python diagnostics.py`を実行 |

**推奨ワークフロー:**
1. カードリーダーを接続
2. USBをWSLにアタッチ（Windows環境）
3. `docker-compose up -d`でコンテナ起動
4. `python diagnostics.py`で確認
