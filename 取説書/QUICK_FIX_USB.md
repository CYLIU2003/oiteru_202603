# カードリーダー即時修正手順

## 🚨 現在の問題

Dockerコンテナ内でカードリーダーが検知されていません。

---

## ✅ 即時修正手順（Windows環境）

### ステップ1: PowerShellを管理者権限で開く

1. スタートメニューで「PowerShell」を検索
2. 右クリック → **「管理者として実行」**

### ステップ2: USBデバイスを確認

```powershell
usbipd list
```

**出力例:**
```
BUSID  VID:PID    DEVICE                                              STATE
1-4    054c:0268  Sony FeliCa Port/PaSoRi                            Not shared
2-3    046d:c52b  Logitech USB Input Device                          Not shared
```

**カードリーダーのBUSID（例: 1-4）をメモしてください。**

### ステップ3: USBデバイスをWSLにアタッチ

```powershell
# BUSIDを環境に合わせて変更してください
usbipd bind --busid 1-4
usbipd attach --wsl --busid 1-4
```

**成功メッセージ:**
```
usbipd: info: Using WSL distribution 'Ubuntu' to attach; the device will be available in all WSL 2 distributions.
usbipd: info: Using IP address 172.x.x.x to reach the host.
```

### ステップ4: WSL内で確認

```bash
# WSLに切り替え（または新しいWSLターミナルを開く）
wsl

# USBデバイスを確認
lsusb
```

**期待される出力:**
```
Bus 001 Device 002: ID 054c:0268 Sony Corp. FeliCa S330 [PaSoRi]
```

### ステップ5: Dockerコンテナを再起動

```bash
cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI
docker-compose up -d
```

### ステップ6: 動作確認

```bash
# コンテナ内のUSBデバイスを確認
docker exec oiteru_flask ls -la /dev/bus/usb/

# 診断を実行
python3 diagnostics.py summary
```

**期待される出力:**
```
[  OK  ] NFCリーダー        3個のUSBデバイスを検出
```

---

## 🔧 usbipd がインストールされていない場合

### インストール方法

```powershell
# wingetを使用（推奨）
winget install usbipd

# または Chocolatey を使用
choco install usbipd-win

# またはGitHubから直接ダウンロード
# https://github.com/dorssel/usbipd-win/releases
```

インストール後、PowerShellを再起動してください。

---

## 🚀 自動起動スクリプトを使用（推奨）

毎回手動でアタッチするのが面倒な場合、自動起動スクリプトを使用してください。

### 使用方法

```powershell
# PowerShellを管理者権限で開く
cd C:\Users\Owner\Desktop\oiteru_250827_restAPI

# スクリプトを実行
.\start_oiteru.ps1

# BUSIDが異なる場合は指定
.\start_oiteru.ps1 -BusId "2-3"
```

このスクリプトは以下を自動で行います:
1. ✅ USBデバイスをWSLにアタッチ
2. ✅ Dockerコンテナを起動
3. ✅ システム診断を実行
4. ✅ 起動状態を確認

---

## ❓ よくある質問

### Q1: "Access is denied" エラーが出る

**A:** PowerShellを管理者権限で実行してください。

### Q2: "usbipd: command not found"

**A:** usbipd-win をインストールしてください。

```powershell
winget install usbipd
```

### Q3: WSLにアタッチしてもコンテナ内で見えない

**A:** 以下を順番に試してください:

1. コンテナを再起動
   ```bash
   docker-compose restart
   ```

2. docker-compose.yml の設定を確認
   ```yaml
   privileged: true
   volumes:
     - /dev/bus/usb:/dev/bus/usb
   ```

3. カードリーダーを抜き差し

4. WSL2を再起動
   ```powershell
   wsl --shutdown
   wsl
   ```

### Q4: 毎回アタッチが必要なのか？

**A:** はい、以下の場合は再アタッチが必要です:

- Windowsを再起動した時
- カードリーダーを抜き差しした時
- WSLを再起動した時

**解決策:** 自動起動スクリプト（`start_oiteru.ps1`）を使用してください。

### Q5: 複数のUSBデバイスをアタッチできる？

**A:** はい、複数のBUSIDを順番にアタッチできます。

```powershell
usbipd attach --wsl --busid 1-4
usbipd attach --wsl --busid 2-3
```

---

## 📋 チェックリスト

修正前に以下を確認してください:

- [ ] PowerShellを管理者権限で開いている
- [ ] usbipd-win がインストールされている
- [ ] カードリーダーがPCに接続されている
- [ ] WSL2 が実行中である
- [ ] Dockerデーモンが起動している

修正後に以下を確認してください:

- [ ] `lsusb` でカードリーダーが表示される
- [ ] `docker exec oiteru_flask ls -la /dev/bus/usb/` でデバイスが表示される
- [ ] `python3 diagnostics.py` で "OK" が表示される
- [ ] 管理画面 (http://localhost:5000/admin) にアクセスできる

---

## 🔗 関連ドキュメント

- [USB_FIX.md](USB_FIX.md) - 詳細な修正ガイド
- [DIAGNOSTICS.md](DIAGNOSTICS.md) - システム診断機能
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング

---

## 💡 今後の予防策

### 方法1: Windowsタスクスケジューラで自動起動

1. タスクスケジューラを開く
2. 「タスクの作成」をクリック
3. トリガー: システム起動時
4. 操作: `start_oiteru.ps1` を実行
5. 「最上位の特権で実行する」にチェック

### 方法2: デスクトップにショートカット作成

1. デスクトップで右クリック → 新規作成 → ショートカット
2. 場所に以下を入力:
   ```
   powershell.exe -ExecutionPolicy Bypass -File "C:\Users\Owner\Desktop\oiteru_250827_restAPI\start_oiteru.ps1"
   ```
3. 名前: 「OITELU起動」
4. ショートカットを右クリック → プロパティ
5. 「詳細設定」→「管理者として実行」にチェック

---

## まとめ

| 状況 | コマンド |
|------|----------|
| **今すぐ修正** | `usbipd attach --wsl --busid 1-4` <br> `docker-compose restart` |
| **自動起動** | `.\start_oiteru.ps1` |
| **確認** | `python3 diagnostics.py summary` |
| **停止** | `docker-compose down` |
