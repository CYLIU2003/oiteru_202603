# NFCカードリーダー Docker対応ガイド

## 概要

Docker環境でNFCカードリーダーを使用するための完全ガイドです。

---

## ⚠️ 重要な前提条件

1. **Windows 11 / Windows 10 (2004以降)**
2. **WSL2が有効**
3. **usbipd-winがインストール済み**

---

## セットアップ手順

### 1. usbipd-winのインストール

```powershell
# PowerShellを管理者として開く

# wingetでインストール（推奨）
winget install --interactive --exact dorssel.usbipd-win

# または、GitHubから直接ダウンロード
# https://github.com/dorssel/usbipd-win/releases
```

インストール後、PCを再起動してください。

### 2. WSL2でのUSBツールインストール

```bash
# WSL2内で実行
sudo apt update
sudo apt install -y usbutils linux-tools-generic hwdata
sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20
```

### 3. カードリーダーをWSL2にアタッチ

#### 方法A: PowerShellスクリプト使用（推奨）

```powershell
# PowerShellを管理者として開く
cd C:\Users\Owner\Desktop\oiteru_250827_restAPI

# スクリプトを実行
.\attach_card_reader.ps1
```

#### 方法B: 手動でアタッチ

```powershell
# 1. 接続されているUSBデバイスを確認
usbipd list

# 出力例:
# BUSID  VID:PID    DEVICE                                                        STATE
# 2-3    054c:06c3  Sony FeliCa Port/PaSoRi, USB Smart Card reader                Not shared

# 2. カードリーダーのBUSIDをメモ（例: 2-3）

# 3. WSL2にアタッチ
usbipd attach --wsl --busid 2-3
```

### 4. WSL2で確認

```bash
# カードリーダーが認識されているか確認
lsusb | grep -i "reader\|nfc\|sony"

# 出力例:
# Bus 001 Device 002: ID 054c:06c3 Sony Corp. FeliCa Port/PaSoRi
```

### 5. Dockerコンテナを起動

```bash
cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI

# コンテナを再ビルド・起動
docker-compose down
docker-compose up -d --build

# ログを確認
docker-compose logs -f
```

### 6. コンテナ内でカードリーダーを確認

```bash
# コンテナに入る
docker exec -it oiteru_flask bash

# カードリーダー初期化スクリプトを実行
./init_card_reader.sh

# 手動でUSBデバイス確認
lsusb | grep -i "reader\|nfc\|sony"

# PC/SCデーモンの状態確認
ps aux | grep pcscd
```

---

## トラブルシューティング

### ❌ カードリーダーが見つからない

#### 確認1: Windows側で認識されているか

```powershell
# PowerShell（管理者）
usbipd list
```

**対処法:**
- USBケーブルを再接続
- 別のUSBポートを試す
- デバイスマネージャーでドライバー確認

#### 確認2: WSL2にアタッチされているか

```powershell
# PowerShell（管理者）
usbipd list

# STATE列が "Attached" になっているか確認
```

**対処法:**
```powershell
# 一度デタッチしてから再アタッチ
usbipd detach --busid 2-3
usbipd attach --wsl --busid 2-3
```

#### 確認3: Dockerコンテナで認識されているか

```bash
# コンテナ内で確認
docker exec -it oiteru_flask lsusb
```

**対処法:**
- Dockerコンテナを再起動
  ```bash
  docker-compose restart
  ```

### ❌ Permission denied エラー

**原因:** USBデバイスへのアクセス権限がない

**対処法:**

```yaml
# docker-compose.ymlで確認
services:
  flask:
    privileged: true  # これが必須
    devices:
      - /dev/bus/usb:/dev/bus/usb
```

### ❌ PC/SC daemon not running

**原因:** PC/SCデーモンが起動していない

**対処法:**

```bash
# コンテナ内で手動起動
docker exec -it oiteru_flask bash
pcscd --debug --apdu --foreground &
```

### ❌ コンテナ起動後にカードリーダーが消える

**原因:** WSL2の再起動などでUSBアタッチが解除される

**対処法:**

```powershell
# PowerShellでスクリプトを再実行
.\attach_card_reader.ps1
```

または、タスクスケジューラで自動実行を設定

---

## 自動化

### Windows起動時に自動アタッチ

#### 方法1: タスクスケジューラ

1. タスクスケジューラを開く
2. 「基本タスクの作成」
3. 設定:
   - **トリガー**: ログオン時
   - **操作**: プログラムの開始
   - **プログラム**: `powershell.exe`
   - **引数**: `-ExecutionPolicy Bypass -File "C:\Users\Owner\Desktop\oiteru_250827_restAPI\attach_card_reader.ps1"`
   - **最上位の特権で実行**: チェック

#### 方法2: スタートアップフォルダ

```powershell
# バッチファイルを作成
$content = @'
@echo off
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\Owner\Desktop\oiteru_250827_restAPI\attach_card_reader.ps1"
'@

$startupPath = [Environment]::GetFolderPath('Startup')
$content | Out-File -FilePath "$startupPath\attach_card_reader.bat" -Encoding ASCII
```

---

## Docker環境での制限事項

### できること ✅

- NFCカードの読み取り（nfcpy）
- PC/SCプロトコル経由でのアクセス
- FeliCa, MIFARE等の一般的なカード
- 複数のカードリーダー対応

### できないこと / 注意点 ❌

- **ホットプラグは非対応**: カードリーダーを抜き差ししたら、WSL2に再アタッチが必要
- **WSL再起動で解除**: WSL2を再起動するとアタッチが解除される
- **コンテナ再起動**: カードリーダーがある場合、PC/SCデーモンも再起動が必要

---

## ベストプラクティス

### 開発環境

**推奨**: ホストマシン（Windows）で直接実行

```bash
# WSL2で実行（Dockerなし）
cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI
python app.py
```

**理由:**
- USBアクセスが確実
- デバッグが容易
- 再起動の手間なし

### 本番環境

**推奨**: Docker環境で実行

```bash
# Dockerで実行
docker-compose up -d
```

**理由:**
- 環境の一貫性
- デプロイが簡単
- 依存関係の管理

ただし、以下を実施:
1. Windows起動時にUSB自動アタッチ設定
2. 定期的な死活監視
3. カードリーダー再接続の自動化スクリプト

---

## 診断コマンド一覧

```bash
# === Windows側 ===
# USBデバイス一覧
usbipd list

# WSL2にアタッチ
usbipd attach --wsl --busid 2-3

# アタッチ解除
usbipd detach --busid 2-3

# === WSL2側 ===
# USBデバイス確認
lsusb

# NFCリーダー特定
lsusb | grep -i "reader\|nfc\|sony\|rc-s"

# === Docker側 ===
# コンテナに入る
docker exec -it oiteru_flask bash

# カードリーダー初期化
./init_card_reader.sh

# USBデバイス確認
lsusb

# PC/SCデーモン確認
ps aux | grep pcscd
pcsc_scan

# Pythonでテスト
python -c "import nfc; print(nfc.ContactlessFrontend('usb'))"
```

---

## まとめ

| 環境 | USB認識 | 簡単さ | 推奨度 |
|------|---------|--------|--------|
| **Windows直接** | ✅ 確実 | ⭐⭐⭐ | 開発時 |
| **WSL2直接** | ✅ 良好 | ⭐⭐ | 開発・テスト |
| **Docker** | ⚠️ 要設定 | ⭐ | 本番環境 |

**開発時**: WSL2で直接実行
**本番時**: Docker + 自動アタッチ設定

詳細は以下も参照:
- [公式usbipd-winドキュメント](https://github.com/dorssel/usbipd-win)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
