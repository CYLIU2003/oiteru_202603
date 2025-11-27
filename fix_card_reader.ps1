# カードリーダー完全修正スクリプト
# PowerShell管理者権限で実行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "カードリーダー完全修正スクリプト" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: カードリーダーをWSL2にアタッチ
Write-Host "Step 1: カードリーダーをWSL2にアタッチ..." -ForegroundColor Yellow
Write-Host ""

# デバイス一覧を表示
Write-Host "現在のUSBデバイス:" -ForegroundColor Gray
usbipd list
Write-Host ""

# カードリーダーのBUSIDを取得
$busid = "1-4"  # Sony RC-S380/S のBUSID
Write-Host "カードリーダー BUSID: $busid" -ForegroundColor Gray

# 既存の接続を解除
Write-Host "既存の接続を解除..." -ForegroundColor Gray
usbipd detach --busid $busid 2>$null
Start-Sleep -Seconds 1

# WSL2にアタッチ
Write-Host "WSL2にアタッチ中..." -ForegroundColor Gray
usbipd attach --wsl --busid $busid --auto-attach

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ アタッチ成功" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "❌ アタッチ失敗" -ForegroundColor Red
    Write-Host "手動で実行してください: usbipd attach --wsl --busid $busid"
    pause
    exit 1
}

# Step 2: WSL2で確認
Write-Host ""
Write-Host "Step 2: WSL2で確認..." -ForegroundColor Yellow
$wslCheck = wsl lsusb | Select-String "054c:06c1"
if ($wslCheck) {
    Write-Host "✅ WSL2でカードリーダー認識: $wslCheck" -ForegroundColor Green
} else {
    Write-Host "❌ WSL2でカードリーダーが見つかりません" -ForegroundColor Red
    wsl lsusb
    pause
    exit 1
}

# Step 3: Dockerコンテナを再起動
Write-Host ""
Write-Host "Step 3: Dockerコンテナを再起動..." -ForegroundColor Yellow
Write-Host "コンテナ停止中..." -ForegroundColor Gray
wsl bash -c "cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI && docker-compose -f docker-compose.mysql.yml down"
Start-Sleep -Seconds 2

Write-Host "コンテナ起動中..." -ForegroundColor Gray
wsl bash -c "cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI && docker-compose -f docker-compose.mysql.yml up -d"
Start-Sleep -Seconds 5

# Step 4: コンテナ内でカードリーダー初期化
Write-Host ""
Write-Host "Step 4: コンテナ内でカードリーダー初期化..." -ForegroundColor Yellow
wsl bash -c "cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI && docker exec oiteru_flask bash -c 'pkill -9 pcscd 2>/dev/null; pcscd; sleep 2'"

# Step 5: 動作確認
Write-Host ""
Write-Host "Step 5: 動作確認..." -ForegroundColor Yellow
Write-Host "pcsc_scanでテスト（5秒間）..." -ForegroundColor Gray
wsl bash -c "docker exec oiteru_flask timeout 5 pcsc_scan 2>&1" | Select-Object -First 20

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "修正完了！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "確認コマンド:" -ForegroundColor Yellow
Write-Host "  wsl lsusb | grep Sony" -ForegroundColor Gray
Write-Host "  wsl docker exec oiteru_flask pcsc_scan" -ForegroundColor Gray
Write-Host ""
Write-Host "Web UI: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
pause
