###############################################################################
# OITERUシステム - 子機環境セットアップスクリプト (Windows開発環境用)
# テスト・開発環境としてWindows上で子機を動作させる場合に使用
###############################################################################

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  OITERUシステム - 子機環境セットアップ" -ForegroundColor Cyan
Write-Host "  (Windows開発環境用)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# --- 1. Python仮想環境の作成 ---
Write-Host "🐍 [1/3] Python仮想環境を作成中..." -ForegroundColor Yellow
Set-Location $ProjectRoot

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ 仮想環境 'venv' を作成しました" -ForegroundColor Green
} else {
    Write-Host "✓ 仮想環境は既に存在します" -ForegroundColor Green
}

# --- 2. Pythonパッケージのインストール ---
Write-Host ""
Write-Host "📚 [2/3] Pythonパッケージをインストール中..." -ForegroundColor Yellow

# 仮想環境を有効化
& "venv\Scripts\Activate.ps1"

# pipを最新版に更新
python -m pip install --upgrade pip setuptools wheel

# 子機用パッケージをインストール
if (Test-Path "docker\requirements-client.txt") {
    # Windowsでは一部のパッケージ(RPi.GPIO等)がインストールできないため、
    # 可能なパッケージのみインストール
    Write-Host "⚠️  注意: Windows環境では一部のRaspberry Pi専用パッケージはスキップされます" -ForegroundColor Yellow
    
    # 基本パッケージのみインストール
    pip install requests flask psutil
    
    Write-Host "✓ 基本パッケージをインストールしました" -ForegroundColor Green
    Write-Host "  - requests" -ForegroundColor Gray
    Write-Host "  - flask" -ForegroundColor Gray
    Write-Host "  - psutil" -ForegroundColor Gray
} else {
    Write-Host "⚠️  requirements-client.txt が見つかりません" -ForegroundColor Yellow
}

# --- 3. 設定ファイルの確認 ---
Write-Host ""
Write-Host "⚙️  [3/3] 設定ファイルを確認中..." -ForegroundColor Yellow

if (-not (Test-Path "config.json")) {
    if (Test-Path "config_templates\config_unit.template.json") {
        Copy-Item "config_templates\config_unit.template.json" "config.json"
        Write-Host "✓ テンプレートからconfig.jsonを作成しました" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  重要: config.jsonを編集して、以下を設定してください:" -ForegroundColor Yellow
        Write-Host "   - SERVER_URL: 親機のURL" -ForegroundColor Gray
        Write-Host "   - UNIT_NAME: この子機の名前" -ForegroundColor Gray
        Write-Host "   - UNIT_PASSWORD: この子機のパスワード" -ForegroundColor Gray
    } else {
        Write-Host "⚠️  config.jsonとテンプレートが見つかりません" -ForegroundColor Yellow
    }
} else {
    Write-Host "✓ config.jsonは既に存在します" -ForegroundColor Green
}

# --- 完了メッセージ ---
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  ✅ セットアップ完了！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 次のステップ:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. config.jsonを編集して設定を完了してください:" -ForegroundColor White
Write-Host "   notepad config.json" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 子機を起動してください (開発モード):" -ForegroundColor White
Write-Host "   venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   python unit.py" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  注意:" -ForegroundColor Yellow
Write-Host "Windows環境では以下の機能は動作しません:" -ForegroundColor Gray
Write-Host "  - NFCカードリーダー (nfcpy)" -ForegroundColor Gray
Write-Host "  - GPIO制御 (RPi.GPIO)" -ForegroundColor Gray
Write-Host "  - I2C通信 (Adafruit-PCA9685)" -ForegroundColor Gray
Write-Host ""
Write-Host "実機での動作確認は Raspberry Pi で行ってください。" -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Cyan
