# PowerShell スクリプト - OITERU親機起動（USBデバイス自動アタッチ付き）
# 管理者権限で実行してください

param(
    [string]$BusId = "1-4"  # カードリーダーのBUSID（環境に合わせて変更）
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OITERU 親機起動スクリプト" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "エラー: このスクリプトは管理者権限で実行する必要があります。" -ForegroundColor Red
    Write-Host "PowerShellを右クリック → '管理者として実行' で開き直してください。" -ForegroundColor Yellow
    pause
    exit 1
}

# 2. usbipd コマンドの存在確認
Write-Host "[1/5] usbipd の確認中..." -ForegroundColor Yellow
$usbipdExists = Get-Command usbipd -ErrorAction SilentlyContinue
if (-not $usbipdExists) {
    Write-Host "エラー: usbipd がインストールされていません。" -ForegroundColor Red
    Write-Host "以下のコマンドでインストールしてください:" -ForegroundColor Yellow
    Write-Host "  winget install usbipd" -ForegroundColor Green
    pause
    exit 1
}
Write-Host "  ✓ usbipd が見つかりました" -ForegroundColor Green

# 3. USBデバイス一覧表示
Write-Host ""
Write-Host "[2/5] 接続されているUSBデバイス:" -ForegroundColor Yellow
usbipd list
Write-Host ""

# 4. USBデバイスをWSLにアタッチ
Write-Host "[3/5] USBデバイス (BUSID: $BusId) をWSLにアタッチ中..." -ForegroundColor Yellow
try {
    # まずbindする
    usbipd bind --busid $BusId 2>&1 | Out-Null
    
    # WSLにアタッチ
    usbipd attach --wsl --busid $BusId
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ USBデバイスをアタッチしました" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ アタッチ中にエラーが発生しましたが続行します..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ USBデバイスのアタッチに失敗しました: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  続行しますが、カードリーダーが動作しない可能性があります。" -ForegroundColor Yellow
}

# 5. WSL内でUSBデバイスを確認
Write-Host ""
Write-Host "[4/5] WSL内でUSBデバイスを確認中..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$usbCheck = wsl -d Ubuntu -e bash -c "lsusb" 2>&1
Write-Host $usbCheck
Write-Host ""

# 6. Dockerコンテナを起動
Write-Host "[5/5] Dockerコンテナを起動中..." -ForegroundColor Yellow
$projectPath = "cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI"
$dockerUp = wsl -d Ubuntu -e bash -c "$projectPath && docker-compose up -d" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Dockerコンテナを起動しました" -ForegroundColor Green
} else {
    Write-Host "  ✗ Dockerコンテナの起動に失敗しました" -ForegroundColor Red
    Write-Host $dockerUp
    pause
    exit 1
}

# 7. 診断を実行
Write-Host ""
Write-Host "システム診断を実行中..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
wsl -d Ubuntu -e bash -c "$projectPath && python3 diagnostics.py summary"

# 8. 完了メッセージ
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  起動完了！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "管理画面: http://localhost:5000/admin" -ForegroundColor Cyan
Write-Host ""
Write-Host "コンテナを停止する場合:" -ForegroundColor Yellow
Write-Host "  wsl -d Ubuntu -e bash -c `"cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI && docker-compose down`"" -ForegroundColor Gray
Write-Host ""

# BUSIDの変更方法を表示
Write-Host "注意: カードリーダーのBUSIDが異なる場合は、以下のように指定してください:" -ForegroundColor Yellow
Write-Host "  .\start_oiteru.ps1 -BusId `"2-3`"" -ForegroundColor Gray
Write-Host ""

pause
