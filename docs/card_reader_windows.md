# Windows の WSL で NFC リーダーを検証する

**対象は開発担当者です。日常の当番や、実機なしのテストにはこの作業は不要です。**
Windows に接続した USB リーダーを WSL 2（Windows 上で Linux を動かす仕組み）へ渡して使います。
親機プログラムも同じ WSL 内で動かす必要があります。Windows 側の親機からは、WSL へ渡したリーダーを使えません。

この手順は [Microsoft 公式の WSL USB 接続手順](https://learn.microsoft.com/en-us/windows/wsl/connect-usb) の
usbipd-win 5 以降の操作を基準にしています。
このリポジトリの標準運用は Linux 親機です。Windows の実機検証は担当者と一緒に行ってください。

## 1. WSL と usbipd を確認する

**Windows の PowerShell：**

```powershell
wsl --list --verbose
usbipd --version
```

使う Linux ディストリビューションが一覧にあり、`VERSION` が `2` であることを確認します。
名前は環境で異なります。決まった Ubuntu バージョンやユーザー名をコピーしないでください。
WSL が未導入なら [Microsoft の WSL インストール手順](https://learn.microsoft.com/en-us/windows/wsl/install) を使います。

usbipd がなければ、公式の案内に従って導入します。

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

導入後に PowerShell を開き直し、もう一度バージョンを確認します。

## 2. リーダーを WSL へ渡す

1. 使用する WSL のターミナルを開き、そのままにする。
2. USB リーダーを接続する。
3. **管理者として開いた Windows PowerShell** で次を実行する。

```powershell
usbipd list
```

リーダーの行にある BUSID を確認します。BUSID は `2-3` などですが、接続先によって変わります。
マウスなど別の USB 機器を選ばないよう、機器名を担当者と確認してください。

**管理者 PowerShell：**

```powershell
$ReaderBusId = Read-Host "リーダーの BUSID"
usbipd bind --busid $ReaderBusId
usbipd list
```

その機器が共有されたことを確認します。次の attach は通常権限でも実行できます。
別の PowerShell を開いた場合は `$ReaderBusId` をもう一度入力します。

```powershell
usbipd attach --wsl --busid $ReaderBusId
usbipd list
```

attach 中のリーダーは Windows の他のアプリから使えなくなります。

## 3. WSL の Linux 側で確認する

**ここからは WSL のターミナルです。PowerShell に貼り付けません。**

```bash
sudo apt update
sudo apt install -y usbutils libusb-1.0-0 python3-venv
lsusb
```

接続したリーダーが一覧に出ることを確認します。
WSL 内に取得した OITERU のフォルダへ移動し、[開発手順](onboarding.md) と同様に `.venv` と依存パッケージを用意します。
Windows 用に作った `.venv` は流用しません。

```bash
.venv/bin/python tools/check_nfc_reader.py
```

成功時は終了コード 0、未検出・読み取り失敗時は 1 を返します。
カードを読む確認が必要なら、次を実行してからテスト用カードを置きます。UID は表示しません。

```bash
.venv/bin/python tools/check_nfc_reader.py --read
```

権限エラーは、USB の udev ルール等を担当者と確認します。親機を root で起動して回避しないでください。
Web 画面を使うには、同じ WSL 内で親機と MySQL の準備も必要です。
[親機セットアップ](setup.md#setup-parent) と、WSL で systemd が使えるかを担当者と確認します。

## 4. 作業後に Windows へ戻す

**Windows PowerShell：**

```powershell
usbipd detach --busid $ReaderBusId
```

再起動や抜き差し後には attach が必要になることがあります。そのたびに `usbipd list` で BUSID を確認します。
旧スクリプトの固定パス・固定 BUSID や、カード番号を表示するテストは使いません。
