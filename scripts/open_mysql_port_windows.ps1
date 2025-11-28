# ========================================
# Windows Firewall - MySQLポート3306を開くスクリプト
# ========================================
# 
# このスクリプトは、Windowsファイアウォールでポート3306（MySQL）を開きます。
# 管理者権限で実行する必要があります。
#
# 【使用方法】
# 1. PowerShellを管理者権限で開く
# 2. cd C:\Users\RTDS_admin\source\repos\CYLIU2003\oiteru_250827_restAPI
# 3. .\scripts\open_mysql_port_windows.ps1
#
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Windows Firewall - MySQL Port 3306" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 管理者権限チェック
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[エラー] このスクリプトは管理者権限で実行する必要があります。" -ForegroundColor Red
    Write-Host ""
    Write-Host "PowerShellを右クリックして「管理者として実行」を選択してください。" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[OK] 管理者権限で実行されています。" -ForegroundColor Green
Write-Host ""

# 既存のファイアウォールルールを確認
Write-Host "既存のMySQLファイアウォールルールを確認中..." -ForegroundColor Cyan
$existingRule = Get-NetFirewallRule -DisplayName "MySQL Server (Port 3306)" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "[情報] 既存のルールが見つかりました。削除して再作成します。" -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "MySQL Server (Port 3306)" -ErrorAction SilentlyContinue
}

# ファイアウォールルールを追加（受信）
Write-Host "ファイアウォールルールを作成中（受信）..." -ForegroundColor Cyan
try {
    New-NetFirewallRule `
        -DisplayName "MySQL Server (Port 3306)" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 3306 `
        -Action Allow `
        -Profile Any `
        -Enabled True `
        -Description "OITELUシステム - MySQLデータベース接続を許可" | Out-Null
    
    Write-Host "[OK] 受信ルールを作成しました。" -ForegroundColor Green
} catch {
    Write-Host "[エラー] 受信ルールの作成に失敗しました: $_" -ForegroundColor Red
    pause
    exit 1
}

# ファイアウォールルールを追加（送信）
Write-Host "ファイアウォールルールを作成中（送信）..." -ForegroundColor Cyan
try {
    New-NetFirewallRule `
        -DisplayName "MySQL Client (Port 3306)" `
        -Direction Outbound `
        -Protocol TCP `
        -RemotePort 3306 `
        -Action Allow `
        -Profile Any `
        -Enabled True `
        -Description "OITELUシステム - MySQL接続を許可（クライアント側）" | Out-Null
    
    Write-Host "[OK] 送信ルールを作成しました。" -ForegroundColor Green
} catch {
    Write-Host "[エラー] 送信ルールの作成に失敗しました: $_" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ファイアウォール設定が完了しました！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 作成されたルールを表示
Write-Host "作成されたファイアウォールルール:" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "MySQL*" | Format-Table DisplayName, Enabled, Direction, Action -AutoSize

Write-Host ""
Write-Host "[次のステップ]" -ForegroundColor Yellow
Write-Host "1. メインサーバーでもポート3306を開く（Linuxの場合）" -ForegroundColor White
Write-Host "2. docker-compose.external-db.ymlのMYSQL_HOSTを確認" -ForegroundColor White
Write-Host "3. docker-compose -f docker-compose.external-db.yml up -d で起動" -ForegroundColor White
Write-Host ""

pause
