# OITERUシステム 親機クイック起動スクリプト (Windows PowerShell)
# 軽量版 - 最小限の設定で素早く起動

param(
    [switch]$Docker,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
OITERUシステム 親機クイック起動スクリプト

使い方:
  .\quick_start_parent.ps1          # 仮想環境モードで起動
  .\quick_start_parent.ps1 -Docker  # Dockerモードで起動

オプション:
  -Docker    Dockerコンテナ内でサーバーを起動
  -Help      このヘルプを表示
"@
    exit 0
}

$ErrorActionPreference = "Stop"

# プロジェクトルート
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExampleFile = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvFile)) {
    Write-Host "❌ .env が見つかりません。" -ForegroundColor Red
    Write-Host "   $EnvExampleFile をコピーし、必須値を設定してから再実行してください。" -ForegroundColor Yellow
    exit 1
}

if ($Docker) {
    Write-Host "🐳 Dockerモードで起動します..." -ForegroundColor Cyan
    
    # Docker起動
    Set-Location $ProjectRoot
    Write-Host "Docker Composeを起動中..." -ForegroundColor Yellow
    docker-compose -f docker-compose.mysql.yml up -d
    
    Write-Host ""
    Write-Host "✅ 親機起動完了！" -ForegroundColor Green
    Write-Host "📡 アクセス: http://localhost:5000" -ForegroundColor Cyan
    Write-Host "🔧 管理画面: http://localhost:5000/admin (.env の OITERU_ADMIN_PASSWORD を使用)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📋 ログ表示: docker-compose -f docker-compose.mysql.yml logs -f" -ForegroundColor Gray
    Write-Host "🛑 停止: docker-compose -f docker-compose.mysql.yml down" -ForegroundColor Gray
    
} else {
    Write-Host "🐍 仮想環境モードで起動します..." -ForegroundColor Cyan
    
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
    
    # MySQLコンテナ起動確認
    Write-Host "MySQL Dockerコンテナを確認中..." -ForegroundColor Yellow
    $MysqlRunning = docker ps --filter "name=oiteru_mysql" --format "{{.Names}}" 2>$null
    
    if (-not $MysqlRunning) {
        Write-Host "MySQLコンテナを起動します..." -ForegroundColor Yellow
        Set-Location $ProjectRoot
        docker-compose -f docker-compose.mysql.yml up -d oiteru_mysql
        Start-Sleep -Seconds 3
        Write-Host "✓ MySQLコンテナ起動完了" -ForegroundColor Green
    } else {
        Write-Host "✓ MySQLコンテナは既に起動中" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "🚀 サーバーを起動します..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📡 アクセス: http://localhost:5000" -ForegroundColor Cyan
    Write-Host "🔧 管理画面: http://localhost:5000/admin (.env の OITERU_ADMIN_PASSWORD を使用)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🛑 停止: Ctrl+C を押してください" -ForegroundColor Gray
    Write-Host ""
    
    # サーバー起動
    Set-Location $ProjectRoot
    & "$VenvPath\Scripts\python.exe" db_server.py
}
