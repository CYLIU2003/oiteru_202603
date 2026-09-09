# OITERU 再起動後自動復帰スクリプト
# 1. MySQL (ポータブル版) を起動
# 2. 親機 (db_server.py) を起動
# 3. WSL2 + Ubuntu 26.04 の NFC セットアップを実行
# 4. セットアップ結果をログに保存

$Log = "$env:USERPROFILE\Desktop\oiteru_202603\logs\startup_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

function Log { param([string]$Msg) Add-Content -Path $Log -Value "[$(Get-Date -Format 'HH:mm:ss')] $Msg" }

Log "=== OITERU 自動復帰開始 ==="

# 1. MySQL 起動（ポート3306が空くのを待つ）
Log "MySQL を起動中..."
Start-Process "C:\Users\PSLAB\mysql8\mysql-8.0.44-winx64\bin\mysqld.exe" -ArgumentList '--basedir="C:\Users\PSLAB\mysql8\mysql-8.0.44-winx64"','--datadir="C:\Users\PSLAB\mysql8\data"','--port=3306','--console' -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(60)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    if (Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue) {
        $ready = $true
        break
    }
}
if ($ready) {
    Log "MySQL 起動確認 OK (port 3306)"
} else {
    Log "WARN: MySQL が 60 秒以内に起動しませんでした"
}

# 2. 親機起動
Start-Sleep -Seconds 5
Log "親機 (db_server.py) を起動中..."
Set-Location "C:\Users\PSLAB\Desktop\oiteru_202603"
Start-Process "C:\Users\PSLAB\Desktop\oiteru_202603\.venv\Scripts\python.exe" -ArgumentList "db_server.py" -WorkingDirectory "C:\Users\PSLAB\Desktop\oiteru_202603"

$deadline = (Get-Date).AddSeconds(60)
$webReady = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $webReady = $true; break }
    } catch {}
}
if ($webReady) {
    Log "親機 起動確認 OK (http://localhost:5000)"
} else {
    Log "WARN: 親機が 60 秒以内に応答しませんでした"
}

# 3. WSL2 + Ubuntu 26.04 + NFC セットアップ
Start-Sleep -Seconds 5
Log "WSL NFC セットアップを実行中..."
& powershell.exe -ExecutionPolicy Bypass -File "C:\Users\PSLAB\Desktop\oiteru_202603\scripts\wsl_nfc_setup.ps1" *>> $Log

Log "=== OITERU 自動復帰 完了 ==="
