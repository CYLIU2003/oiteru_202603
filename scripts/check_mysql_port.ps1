# ========================================
# ポート3306の開放状態を確認するスクリプト（Windows）
# ========================================
# 
# このスクリプトは、ポート3306が開いているか確認します。
#
# 【使用方法】
# .\scripts\check_mysql_port.ps1
#
# ========================================

param(
    [string]$TargetHost = "localhost"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MySQL Port 3306 接続チェック" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 1. ローカルファイアウォールルールの確認
# ========================================
Write-Host "[1] Windowsファイアウォールルールの確認" -ForegroundColor Yellow
Write-Host ""

$rules = Get-NetFirewallRule -DisplayName "MySQL*" -ErrorAction SilentlyContinue

if ($rules) {
    Write-Host "[OK] MySQLファイアウォールルールが見つかりました:" -ForegroundColor Green
    $rules | Format-Table DisplayName, Enabled, Direction, Action -AutoSize
} else {
    Write-Host "[警告] MySQLファイアウォールルールが見つかりません。" -ForegroundColor Yellow
    Write-Host "以下のコマンドでルールを追加できます:" -ForegroundColor White
    Write-Host "  .\scripts\open_mysql_port_windows.ps1" -ForegroundColor Cyan
}

Write-Host ""

# ========================================
# 2. ポートリスニング状態の確認
# ========================================
Write-Host "[2] ポート3306のリスニング状態を確認" -ForegroundColor Yellow
Write-Host ""

$listening = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue

if ($listening) {
    Write-Host "[OK] ポート3306でリスニング中:" -ForegroundColor Green
    $listening | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
    
    # プロセス名を取得
    $listening | ForEach-Object {
        $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  プロセス: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "[警告] ポート3306でリスニングしているプロセスが見つかりません。" -ForegroundColor Yellow
    Write-Host "MySQLサーバーが起動していない可能性があります。" -ForegroundColor White
}

Write-Host ""

# ========================================
# 3. リモートホストへの接続テスト
# ========================================
Write-Host "[3] リモートホストへの接続テスト: $TargetHost" -ForegroundColor Yellow
Write-Host ""

try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $asyncResult = $tcpClient.BeginConnect($TargetHost, 3306, $null, $null)
    $waitHandle = $asyncResult.AsyncWaitHandle
    
    if ($waitHandle.WaitOne(3000, $false)) {
        try {
            $tcpClient.EndConnect($asyncResult)
            Write-Host "[OK] $TargetHost:3306 への接続に成功しました。" -ForegroundColor Green
            $tcpClient.Close()
        } catch {
            Write-Host "[エラー] $TargetHost:3306 への接続に失敗しました: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "[エラー] $TargetHost:3306 への接続がタイムアウトしました（3秒）。" -ForegroundColor Red
        $tcpClient.Close()
    }
} catch {
    Write-Host "[エラー] 接続テスト中にエラーが発生しました: $_" -ForegroundColor Red
}

Write-Host ""

# ========================================
# 4. Dockerコンテナの確認
# ========================================
Write-Host "[4] Dockerコンテナの確認" -ForegroundColor Yellow
Write-Host ""

try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "mysql|3306"
    
    if ($containers) {
        Write-Host "[OK] MySQL関連のコンテナが見つかりました:" -ForegroundColor Green
        $containers | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
    } else {
        Write-Host "[警告] MySQL関連のコンテナが見つかりません。" -ForegroundColor Yellow
        Write-Host "以下のコマンドでコンテナを起動できます:" -ForegroundColor White
        Write-Host "  docker-compose -f docker-compose.multi-server.yml up -d" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[情報] Docker環境が見つかりません。" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  チェック完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# トラブルシューティング
# ========================================
Write-Host "[トラブルシューティング]" -ForegroundColor Yellow
Write-Host ""
Write-Host "接続できない場合の確認事項:" -ForegroundColor White
Write-Host "1. ファイアウォールルールが有効になっているか" -ForegroundColor White
Write-Host "2. MySQLサーバーが起動しているか (docker ps)" -ForegroundColor White
Write-Host "3. MySQLの設定でbind-address=0.0.0.0になっているか" -ForegroundColor White
Write-Host "4. MySQL側のユーザー権限が正しく設定されているか" -ForegroundColor White
Write-Host ""
Write-Host "詳細な接続テスト:" -ForegroundColor White
Write-Host "  .\scripts\check_mysql_port.ps1 -TargetHost <IPアドレス>" -ForegroundColor Cyan
Write-Host ""
