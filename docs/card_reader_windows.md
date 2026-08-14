# Windows 開発機で RC-S380 カードリーダーを使う手順

対象: Windows PC で OITERU 親機を動作させる開発環境

## 推奨: WSL2 + usbipd 経由（2026-08-06 実証済み）

Windows 側の SONY 公式ドライバを残したまま、RC-S380 を WSL2 に渡して
Linux 側（標準構成）で nfcpy を使う方法。ドライバ置き換え不要。

### 手順

```powershell
# 1. Ubuntu をインストール（未インストールの場合）
winget install -e --id Canonical.Ubuntu.2404 --accept-source-agreements --accept-package-agreements --disable-interactivity

# 2. usbipd-win をインストール
winget install -e --id dorssel.usbipd-win --accept-source-agreements --accept-package-agreements --disable-interactivity

# 3. Ubuntu を WSL に登録（root ユーザーで初回登録）
& "$env:LOCALAPPDATA\Microsoft\WindowsApps\ubuntu2404.exe" install --root

# 4. WSL2 を起動したまま維持（バックグラウンドで sleep を実行）
Start-Process wsl.exe -ArgumentList '-d','Ubuntu-24.04','--','bash','-c','sleep 3600'

# 5. カードリーダーの BUSID を確認（RC-S380 は 054c:06c3）
usbipd list

# 6. bind + attach（管理者権限が必要。UAC プロンプトで「はい」）
Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','usbipd bind --busid 2-3; usbipd attach --wsl --busid 2-3 --auto-attach'

# 7. WSL2 内で認識確認
wsl -d Ubuntu-24.04 -- lsusb   # → "Bus 001 Device 002: ID 054c:06c3 Sony Corp. RC-S380"

# 8. WSL2 内に Python + nfcpy をセットアップ
wsl -d Ubuntu-24.04 -- apt-get install -y python3-pip python3-venv python3-dev libusb-1.0-0
wsl -d Ubuntu-24.04 -- python3 -m venv /opt/oiteru-venv
wsl -d Ubuntu-24.04 -- /opt/oiteru-venv/bin/pip install nfcpy

# 9. 動作確認
wsl -d Ubuntu-24.04 -- /opt/oiteru-venv/bin/python -c "import nfc; clf=nfc.ContactlessFrontend('usb'); print('OPEN OK:', clf); clf.close()"
```

### 注意

- attach 中は Windows 側からリーダーは見えなくなる（WSL 側に移動する）。
- 親機サーバーも WSL2 内で起動する必要がある（Windows 側の server.py からは
  リーダーにアクセスできない）。
- アタッチ解除: `usbipd detach --busid 2-3`（管理者権限）。

## 旧手順（Windows 直接 + Zadig）※非推奨

Windows 側の `server.py` を直接起動する構成で、SONY 公式ドライバが
libusb をブロックする問題への対処。

## 2. 必要なもの

- `tools/zadig-2.9.exe`（このリポジトリに同梱済み。公式: https://zadig.akeo.ie/）
- 管理者権限

## 3. ドライバ置き換え手順（Zadig）

1. `tools/zadig-2.9.exe` を**右クリック → 「管理者として実行」**。
2. メニュー **Options → List All Devices** にチェックを入れる。
3. 上部プルダウンで **Sony NFC Port/PaSoRi 100 USB**（または
   `USB\VID_054C&PID_06C3` を含む項目）を選択。
4. 右側のドライバ選択で **WinUSB** を選択。
5. 青色の **Replace Driver** ボタンをクリック。
6. 警告ダイアログが出たら **Yes**（または Install）を選択。
7. 「Driver installed successfully」と表示されたら完了。

> 注意: 置き換え後、USB ケーブルの抜き差しが必要な場合があります。

## 4. 動作確認

PowerShell で以下を実行（リーダーは PC に接続したまま）:

```powershell
cd c:\oiteru_202603
c:/oiteru_202603/.venv/Scripts/python.exe -c "import nfc; clf = nfc.ContactlessFrontend('usb'); print('OPEN OK:', clf); clf.close()"
```

- `OPEN OK: ...` と表示されれば成功。
- `USBErrorNotSupported` のままなら、Zadig の手順をやり直すか、
  デバイスマネージャーでドライバが WinUSB になっているか確認。

ブラウザで確認:

- http://localhost:5000/register を開き「再確認」を押す。
  「ICカードリーダーが接続されていません」が消えていれば OK。

## 5. 元に戻す方法（SONY 公式ドライバに復元）

- デバイスマネージャー → 「NFC Port/PaSoRi 100 USB」を右クリック →
  「ドライバーの更新」→「コンピューターを参照してドライバーを検索」→
  「コンピューター上の利用可能なドライバーの一覧から選択」→
  「NFC Port/PaSoRi 100 USB」を選択してインストール。
- または Zadig で再度開き、ドライバを「NFC Port/PaSoRi 100 USB」に
  置き換え（*USB デバイスクラスのドライバを入れ替える*場合は手動選択）。

## 6. 注意事項

- ドライバ置き換え後、おサイフケータイ連携など SONY ドライバを
  使う他のアプリはこのリーダーを使えなくなる可能性があります。
- 親機サーバーの再起動は不要です（カード読み取りはリクエスト時に
  リーダーを開く実装のため）。
- Linux / WSL2 で使う場合はこの手順は不要です
  （`scripts/attach_card_reader.ps1` など、usbipd 経由の既存手順を使用）。
