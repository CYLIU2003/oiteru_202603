<#
.SYNOPSIS
OITERU WSL2 + Ubuntu 26.04 + NFCカードリーダー セットアップスクリプト

.DESCRIPTION
Windows再起動後に、以下を実行します:
1. WSL2でUbuntu 26.04が登録されているか確認し、なければインストール
2. Ubuntu内にnfcpy / libusb 環境を構築
3. NFCカードリーダー(PaSoRi RC-S380等)を検出してWSL2にアタッチ
4. カード読み取りの動作確認

使い方:
    .\scripts\windows\wsl_nfc_setup.ps1            # 標準セットアップ
    .\scripts\windows\wsl_nfc_setup.ps1 -ReadCard  # 最後にカード読み取りテストも実行

※ usbipd の bind/attach には管理者権限が必要です。
   スクリプトが管理者権限でない場合は、カードリーダーアタッチだけ別途
   管理者PowerShellで実行してください。
#>

param(
    [switch]$ReadCard,
    [string]$Distro = "Ubuntu-26.04"
)

$ErrorActionPreference = "Continue"
$Usbipd = "C:\Program Files\usbipd-win\usbipd.exe"

function Write-Step { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-OK   { param([string]$Msg) Write-Host "  [OK] $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }

# ---------- 1. WSL / ディストリビューション確認 ----------
Write-Step "1. WSL2 + $Distro の確認"
wsl.exe --status 2>&1 | Out-String | Write-Host

$installed = wsl.exe --list -q 2>&1 | Select-String -Pattern $Distro -Quiet
if (-not $installed) {
    Write-Warn "$Distro が未登録です。インストールします（初回は数分かかります）..."
    wsl.exe --install -d $Distro
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "インストールに失敗しました。Windows再起動後に再実行してください。"
    }
    # 再起動が必要な場合はここで終了
    $still = wsl.exe --list -q 2>&1 | Select-String -Pattern $Distro -Quiet
    if (-not $still) {
        Write-Warn "インストールが保留中です。Windowsを再起動してから再実行してください。"
        exit 1
    }
} else {
    Write-OK "$Distro は登録済みです"
}

# ---------- 2. Ubuntu初期セットアップ ----------
Write-Step "2. Ubuntu内のNFC環境構築"
# 初回起動時はユーザー作成が求められる。--rootで実行して自動化する。
wsl.exe -d $Distro --user root -e bash -lc "export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv libusb-1.0-0 usbutils pcscd 2>&1 | tail -3"
Write-OK "nfcpy/libusbの依存をインストールしました"

wsl.exe -d $Distro --user root -e bash -lc "pip3 install --break-system-packages nfcpy 2>&1 | tail -2"
Write-OK "nfcpy をインストールしました"

wsl.exe -d $Distro --user root -e bash -lc "python3 -c 'import nfc; print(\"nfcpy\", nfc.__version__)'"
Write-OK "nfcpy の動作を確認しました"

# ---------- 3. カードリーダーのアタッチ ----------
Write-Step "3. NFCカードリーダーのWSLアタッチ"

if (-not (Test-Path $Usbipd)) {
    Write-Warn "usbipd-win が見つかりません: $Usbipd"
    Write-Warn "winget install dorssel.usbipd-win を実行してください。"
} else {
    & $Usbipd list

    # NFCリーダーを検索 (Sony PaSoRi: 054c:06c3 / 054c:06c1 / 054c:02e1)
    $readers = (& $Usbipd list) | Select-String -Pattern "054c:06c3|054c:06c1|054c:02e1|rc-s380|rc-s370|pasori" 
    if (-not $readers) {
        Write-Warn "NFCカードリーダーが見つかりません。USBポートへの接続・挿し直しを確認してください。"
        Write-Warn "接続後、このスクリプトを再実行するか、以下の手動コマンドを実行してください:"
        Write-Warn "  usbipd bind --busid <BUSID>"
        Write-Warn "  usbipd attach --wsl --busid <BUSID> --auto-attach"
    } else {
        Write-OK "カードリーダーを検出しました:"
        $readers | ForEach-Object { Write-Host "    $_" }
        $busid = ($readers[0] -split '\s+')[0]

        # 管理者チェック
        $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if (-not $isAdmin) {
            Write-Warn "bind/attachには管理者権限が必要です。管理者PowerShellで以下を実行してください:"
            Write-Warn "  usbipd bind --busid $busid"
            Write-Warn "  usbipd attach --wsl --busid $busid --auto-attach"
        } else {
            & $Usbipd bind --busid $busid 2>&1 | Out-Host
            & $Usbipd attach --wsl --busid $busid --auto-attach 2>&1 | Out-Host
            Start-Sleep -Seconds 2
            wsl.exe -d $Distro --user root -e bash -lc "lsusb | grep -i '054c\|sony' || lsusb"
        }
    }
}

# ---------- 4. カード読み取りテスト ----------
if ($ReadCard) {
    Write-Step "4. カード読み取りテスト（10秒待機）"
    wsl.exe -d $Distro --user root -e bash -lc "python3 -c \"
import nfc, time
clf = nfc.ContactlessFrontend('usb')
if not clf:
    print('FAIL: リーダーを開けません')
    exit(1)
print('リーダー:', clf)
start = time.time()
while time.time() - start < 10:
    t = clf.sense(nfc.clf.RemoteTarget('106A'), nfc.clf.RemoteTarget('106B'), nfc.clf.RemoteTarget('212F'), iterations=5, interval=0.1)
    if t:
        tag = nfc.tag.activate(clf, t)
        if tag:
            print('OK: card_id =', tag.identifier.hex().upper())
            break
else:
    print('FAIL: カードを読み取れませんでした')
clf.close()
\""
}

Write-Host ""
Write-Host "セットアップ完了。親機を再起動する場合は:" -ForegroundColor Green
Write-Host "  MySQL : C:\Users\PSLAB\mysql8\mysql-8.0.44-winx64\bin\mysqld.exe --basedir=\"C:\Users\PSLAB\mysql8\mysql-8.0.44-winx64\" --datadir=\"C:\Users\PSLAB\mysql8\data\" --port=3306 --console" -ForegroundColor Gray
Write-Host "  親機  : .\.venv\Scripts\python.exe db_server.py" -ForegroundColor Gray
