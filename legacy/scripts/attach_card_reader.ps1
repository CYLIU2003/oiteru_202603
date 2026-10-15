# USB/NFCカードリーダーをWSL2にアタッチするスクリプト
# 管理者権限で実行してください

# エラーが発生してもスクリプトを継続
$ErrorActionPreference = "Continue"

Write-Host "=========================================="
Write-Host "USB/NFCカードリーダー WSL2アタッチスクリプト"
Write-Host "=========================================="
Write-Host ""

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "エラー: このスクリプトは管理者権限で実行してください" -ForegroundColor Red
    Write-Host "PowerShellを右クリック → '管理者として実行' で開いてください"
    pause
    exit 1
}

# WSL2が起動しているか確認
Write-Host "0. WSL2の起動確認..."
$wslStatus = wsl --status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ⚠ WSL2が起動していません。起動します..." -ForegroundColor Yellow
    wsl --set-default-version 2
    Start-Sleep -Seconds 2
}
Write-Host "   ✓ WSL2が利用可能です" -ForegroundColor Green

# usbipdがインストールされているか確認
Write-Host "1. usbipd-winの確認..."
$usbipd = Get-Command usbipd -ErrorAction SilentlyContinue

if (-not $usbipd) {
    Write-Host "   エラー: usbipd-winがインストールされていません" -ForegroundColor Red
    Write-Host ""
    Write-Host "以下のURLからインストールしてください:"
    Write-Host "https://github.com/dorssel/usbipd-win/releases"
    pause
    exit 1
}

Write-Host "   ✓ usbipd-winが見つかりました" -ForegroundColor Green

# USBデバイス一覧を表示
Write-Host ""
Write-Host "2. 接続されているUSBデバイス一覧:"
Write-Host "----------------------------------------"
usbipd list

# カードリーダーを検索
Write-Host ""
Write-Host "3. NFCカードリーダーを検索中..."

$readers = usbipd list | Select-String -Pattern "reader|nfc|card|sony|rc-s" -AllMatches

if ($readers) {
    Write-Host "   ✓ 以下のカードリーダーが見つかりました:" -ForegroundColor Green
    $readers | ForEach-Object { Write-Host "     $_" }
    
    Write-Host ""
    Write-Host "4. カードリーダーをWSL2にアタッチします..."
    
    # BUSIDを抽出（最初のカードリーダー）
    $busid = ($readers[0] -split '\s+')[0]
    
    Write-Host "   BUSID: $busid"
    
    # 既にアタッチされている場合はデタッチ
    Write-Host "   既存の接続をクリア..."
    try {
        usbipd detach --busid $busid 2>$null
        Start-Sleep -Seconds 1
        Write-Host "   ✓ 既存の接続をクリアしました" -ForegroundColor Green
    } catch {
        Write-Host "   (既存の接続なし)" -ForegroundColor Gray
    }
    
    # WSL2にアタッチ
    Write-Host "   WSL2にアタッチ中..."
    try {
        usbipd attach --wsl --busid $busid --auto-attach
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✓ カードリーダーをWSL2にアタッチしました" -ForegroundColor Green
            Start-Sleep -Seconds 2
            
            # WSL2で確認
            Write-Host ""
            Write-Host "5. WSL2でデバイスを確認中..."
            $wslDevices = wsl lsusb
            $cardReader = $wslDevices | Select-String -Pattern "sony|054c|rc-s" -AllMatches
            
            if ($cardReader) {
                Write-Host "   ✓ カードリーダーがWSL2で認識されました:" -ForegroundColor Green
                Write-Host "     $cardReader"
            } else {
                Write-Host "   ⚠ WSL2でカードリーダーが見つかりませんでした" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "   全USBデバイス一覧:"
                $wslDevices | ForEach-Object { Write-Host "     $_" }
            }
            
            Write-Host ""
            Write-Host "=========================================="
            Write-Host "アタッチ完了！" -ForegroundColor Green
            Write-Host "=========================================="
            Write-Host ""
            Write-Host "次のステップ:"
            Write-Host "1. WSL2ターミナルでカードリーダーを確認:"
            Write-Host "   wsl lsusb | grep Sony"
            Write-Host ""
            Write-Host "2. Dockerコンテナを再起動してください:"
            Write-Host "   wsl"
            Write-Host "   cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI"
            Write-Host "   docker-compose -f docker-compose.mysql.yml down"
            Write-Host "   docker-compose -f docker-compose.mysql.yml up -d"
            Write-Host ""
            Write-Host "3. コンテナ内でカードリーダーを確認:"
            Write-Host "   docker exec -it oiteru_flask bash"
            Write-Host "   ./init_card_reader.sh"
            Write-Host "   pcsc_scan"
            
        } else {
            Write-Host "   ✗ アタッチに失敗しました (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
            Write-Host ""
            Write-Host "トラブルシューティング:"
            Write-Host "1. WSL2を再起動してみてください: wsl --shutdown"
            Write-Host "2. Windowsを再起動してみてください"
            Write-Host "3. usbipd-winを再インストールしてください"
        }
    } catch {
        Write-Host "   ✗ エラーが発生しました: $_" -ForegroundColor Red
    }
    
} else {
    Write-Host "   ⚠ カードリーダーが見つかりませんでした" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "トラブルシューティング:"
    Write-Host "- USBケーブルが正しく接続されているか確認"
    Write-Host "- デバイスマネージャーでドライバーが正常か確認"
    Write-Host "- 別のUSBポートに接続してみる"
}

Write-Host ""
pause
