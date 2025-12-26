# =========================================
# OITELU ランチャー起動スクリプト (Windows PowerShell)
# =========================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OITELU System Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "どちらのランチャーを起動しますか？" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. GUI版 (グラフィカルインターフェース)" -ForegroundColor White
Write-Host "  2. CUI版 (BIOS風テキストインターフェース)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "選択してください [1-2]"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "GUI版ランチャーを起動しています..." -ForegroundColor Green
    python launcher_gui.py
} elseif ($choice -eq "2") {
    Write-Host ""
    Write-Host "CUI版ランチャーを起動しています..." -ForegroundColor Green
    python launcher_cui.py
} else {
    Write-Host ""
    Write-Host "無効な選択です。デフォルトでGUI版を起動します。" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    python launcher_gui.py
}

Write-Host ""
Read-Host "Press Enter to exit"
