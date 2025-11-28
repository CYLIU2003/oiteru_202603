# UTF-8エンコーディングを設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

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
Write-Host "  MySQL Port 3306 Connection Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# 1. Local Firewall Rules Check
# ========================================
Write-Host "[1] Windows Firewall Rules Check" -ForegroundColor Yellow
Write-Host ""

$rules = Get-NetFirewallRule -DisplayName "MySQL*" -ErrorAction SilentlyContinue

if ($rules) {
    Write-Host "[OK] MySQL firewall rules found:" -ForegroundColor Green
    $rules | Format-Table DisplayName, Enabled, Direction, Action -AutoSize
} else {
    Write-Host "[WARNING] MySQL firewall rules not found." -ForegroundColor Yellow
    Write-Host "You can add rules with:" -ForegroundColor White
    Write-Host "  .\scripts\open_mysql_port_windows.ps1" -ForegroundColor Cyan
}

Write-Host ""

# ========================================
# 2. Port 3306 Listening Status Check
# ========================================
Write-Host "[2] Port 3306 Listening Status Check" -ForegroundColor Yellow
Write-Host ""

$listening = Get-NetTCPConnection -LocalPort 3306 -State Listen -ErrorAction SilentlyContinue

if ($listening) {
    Write-Host "[OK] Listening on port 3306:" -ForegroundColor Green
    $listening | Format-Table LocalAddress, LocalPort, State, OwningProcess -AutoSize
    
    # Get process name
    $listening | ForEach-Object {
        $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  Process: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host "[WARNING] No process listening on port 3306." -ForegroundColor Yellow
    Write-Host "MySQL server may not be running." -ForegroundColor White
}

Write-Host ""

# ========================================
# 3. Remote Host Connection Test
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
            Write-Host "[OK] Successfully connected to ${TargetHost}:3306" -ForegroundColor Green
            $tcpClient.Close()
        } catch {
            Write-Host "[ERROR] Failed to connect to ${TargetHost}:3306: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "[ERROR] Connection to ${TargetHost}:3306 timed out (3 seconds)" -ForegroundColor Red
        $tcpClient.Close()
    }
} catch {
    Write-Host "[ERROR] Error during connection test: $_" -ForegroundColor Red
}

Write-Host ""

# ========================================
# 4. Docker Container Check
# ========================================
Write-Host "[4] Docker Container Check" -ForegroundColor Yellow
Write-Host ""

try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "mysql|3306"
    
    if ($containers) {
        Write-Host "[OK] MySQL-related containers found:" -ForegroundColor Green
        $containers | ForEach-Object { Write-Host "  $_" -ForegroundColor Cyan }
    } else {
        Write-Host "[WARNING] No MySQL-related containers found." -ForegroundColor Yellow
        Write-Host "You can start containers with:" -ForegroundColor White
        Write-Host "  docker-compose -f docker-compose.multi-server.yml up -d" -ForegroundColor Cyan
    }
} catch {
    Write-Host "[INFO] Docker environment not found." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Check Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========================================
# Troubleshooting
# ========================================
Write-Host "[Troubleshooting]" -ForegroundColor Yellow
Write-Host ""
Write-Host "If connection fails, check:" -ForegroundColor White
Write-Host "1. Firewall rules are enabled" -ForegroundColor White
Write-Host "2. MySQL server is running (docker ps)" -ForegroundColor White
Write-Host "3. MySQL bind-address=0.0.0.0 in configuration" -ForegroundColor White
Write-Host "4. MySQL user permissions are correct" -ForegroundColor White
Write-Host ""
Write-Host "Detailed connection test:" -ForegroundColor White
Write-Host "  .\scripts\check_mysql_port.ps1 -TargetHost <IP Address>" -ForegroundColor Cyan
Write-Host ""
