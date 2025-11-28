# UTF-8エンコーディングを設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ========================================
# Windows Firewall - MySQL Port 3306
# ========================================
# 
# This script opens port 3306 (MySQL) in Windows Firewall.
# Administrator privileges required.
#
# [Usage]
# 1. Open PowerShell as Administrator
# 2. cd C:\Users\RTDS_admin\source\repos\CYLIU2003\oiteru_250827_restAPI
# 3. .\scripts\open_mysql_port_windows.ps1
#
# ========================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Windows Firewall - MySQL Port 3306" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Administrator privileges check
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script requires administrator privileges." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[OK] Running with administrator privileges." -ForegroundColor Green
Write-Host ""

# Check existing firewall rules
Write-Host "Checking existing MySQL firewall rules..." -ForegroundColor Cyan
$existingRule = Get-NetFirewallRule -DisplayName "MySQL Server (Port 3306)" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "[INFO] Existing rule found. Removing and recreating..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "MySQL Server (Port 3306)" -ErrorAction SilentlyContinue
}

# Add firewall rule (Inbound)
Write-Host "Creating firewall rule (Inbound)..." -ForegroundColor Cyan
try {
    New-NetFirewallRule `
        -DisplayName "MySQL Server (Port 3306)" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 3306 `
        -Action Allow `
        -Profile Any `
        -Enabled True `
        -Description "OITELU System - Allow MySQL database connections" | Out-Null
    
    Write-Host "[OK] Inbound rule created." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to create inbound rule: $_" -ForegroundColor Red
    pause
    exit 1
}

# Add firewall rule (Outbound)
Write-Host "Creating firewall rule (Outbound)..." -ForegroundColor Cyan
try {
    New-NetFirewallRule `
        -DisplayName "MySQL Client (Port 3306)" `
        -Direction Outbound `
        -Protocol TCP `
        -RemotePort 3306 `
        -Action Allow `
        -Profile Any `
        -Enabled True `
        -Description "OITELU System - Allow MySQL connections (Client side)" | Out-Null
    
    Write-Host "[OK] Outbound rule created." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to create outbound rule: $_" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Firewall Configuration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Display created rules
Write-Host "Created firewall rules:" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "MySQL*" | Format-Table DisplayName, Enabled, Direction, Action -AutoSize

Write-Host ""
Write-Host "[Next Steps]" -ForegroundColor Yellow
Write-Host "1. Open port 3306 on main server (Linux)" -ForegroundColor White
Write-Host "2. Check MYSQL_HOST in docker-compose.external-db.yml" -ForegroundColor White
Write-Host "3. Start with: docker-compose -f docker-compose.external-db.yml up -d" -ForegroundColor White
Write-Host ""

pause
