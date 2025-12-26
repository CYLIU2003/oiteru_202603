# OITERUシステム 従親機クイック起動スクリプト (Windows PowerShell)
# 軽量版 - 最小限の設定で素早く起動

param(
    [Parameter(Mandatory=$true)]
    [string]$Host,
    [switch]$Help
)

if ($Help -or -not $Host) {
    Write-Host @"
OITERUシステム 従親機クイック起動スクリプト

使い方:
  .\quick_start_sub.ps1 -Host 192.168.1.100
  .\quick_start_sub.ps1 -Host 100.114.99.67  # Tailscale IP

パラメータ:
  -Host      親機のIPアドレス（必須）
  -Help      このヘルプを表示
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# プロジェクトルート
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "🐍 従親機を起動します..." -ForegroundColor Cyan
Write-Host "📡 接続先親機: $Host" -ForegroundColor Yellow

# 仮想環境パス検出
$VenvPath = $null
$VenvCandidates = @(
    "C:\Users\Owner\.venv_oiteru",
    "$env:USERPROFILE\.venv_oiteru",
    "$ProjectRoot\.venv",
    "$ProjectRoot\venv"
)

foreach ($path in $VenvCandidates) {
    if (Test-Path "$path\Scripts\Activate.ps1") {
        $VenvPath = $path
        Write-Host "✓ 仮想環境を検出: $VenvPath" -ForegroundColor Green
        break
    }
}

if (-not $VenvPath) {
    Write-Host "⚠ 仮想環境が見つかりません。作成します..." -ForegroundColor Yellow
    $VenvPath = "C:\Users\Owner\.venv_oiteru"
    python -m venv $VenvPath
    Write-Host "✓ 仮想環境を作成: $VenvPath" -ForegroundColor Green
    
    # パッケージインストール
    & "$VenvPath\Scripts\pip.exe" install -r "$ProjectRoot\requirements.txt" -q
    & "$VenvPath\Scripts\pip.exe" install pymysql -q
    Write-Host "✓ パッケージをインストールしました" -ForegroundColor Green
}

# 環境変数設定
$env:DB_TYPE = 'mysql'
$env:MYSQL_HOST = $Host
$env:MYSQL_PORT = '3306'
$env:MYSQL_DATABASE = 'oiteru'
$env:MYSQL_USER = 'oiteru_user'
$env:MYSQL_PASSWORD = 'oiteru_password_2025'

Write-Host ""
Write-Host "🚀 サーバーを起動します..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📡 アクセス: http://localhost:5000" -ForegroundColor Cyan
Write-Host "🔧 管理画面: http://localhost:5000/admin (パスワード: admin)" -ForegroundColor Cyan
Write-Host ""
Write-Host "🛑 停止: Ctrl+C を押してください" -ForegroundColor Gray
Write-Host ""

# サーバー起動
Set-Location $ProjectRoot
& "$VenvPath\Scripts\python.exe" server.py
