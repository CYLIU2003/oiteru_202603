#!/bin/bash
#
# OITERUシステム 子機起動スクリプト (Raspberry Pi用)
#
# 仮想環境を自動検出・作成し、子機クライアントを起動します。
#
# 使用方法:
#   sudo ./start_unit.sh --host 192.168.1.100
#   sudo ./start_unit.sh --host 192.168.1.100 --unit-id 1
#   sudo ./start_unit.sh --host 192.168.1.100 --auto
#
# パラメータ:
#   --host        親機のIPアドレス（必須または--auto）
#   --unit-id     子機ID（デフォルト: 自動取得）
#   --port        親機のポート番号（デフォルト: 5000）
#   --auto        自動起動モード（設定ファイルから読み込み）
#   --find-server 親機を自動探知
#   --gui         GUIモードで起動（デフォルト: CUIモード）
#   --help        ヘルプを表示
#

set -e

# ========================================
# カラー定義
# ========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# メッセージ関数
log_status() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${CYAN}$1${NC}"
}

log_success() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${RED}✗ $1${NC}"
}

# ========================================
# デフォルト値
# ========================================
SERVER_HOST=""
SERVER_PORT=5000
UNIT_ID=""
AUTO_MODE=false
FIND_SERVER=false
GUI_MODE=false

# ========================================
# ヘルプ表示
# ========================================
show_help() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║         OITERUシステム 子機起動スクリプト                ║"
    echo "║              (Raspberry Pi用)                            ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "使用方法:"
    echo "  sudo $0 --host <親機IP> [オプション]"
    echo "  sudo $0 --auto"
    echo "  sudo $0 --find-server"
    echo ""
    echo "起動モード:"
    echo "  --host          親機のIPアドレスを指定して起動"
    echo "  --auto          設定ファイルから自動起動"
    echo "  --find-server   ネットワーク上の親機を自動探知"
    echo ""
    echo "オプション:"
    echo "  --unit-id       子機ID（省略時は自動取得）"
    echo "  --port          親機のポート番号（デフォルト: 5000）"
    echo "  --gui           GUIモードで起動"
    echo "  --help          このヘルプを表示"
    echo ""
    echo "例:"
    echo "  sudo $0 --host 192.168.1.100"
    echo "  sudo $0 --host 192.168.1.100 --unit-id 1"
    echo "  sudo $0 --auto"
    echo "  sudo $0 --find-server"
    echo ""
    echo "注意:"
    echo "  NFCリーダーを使用するにはsudo権限が必要です"
    echo ""
    exit 0
}

# ========================================
# 引数解析
# ========================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            SERVER_HOST="$2"
            shift 2
            ;;
        --unit-id)
            UNIT_ID="$2"
            shift 2
            ;;
        --port)
            SERVER_PORT="$2"
            shift 2
            ;;
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --find-server)
            FIND_SERVER=true
            shift
            ;;
        --gui)
            GUI_MODE=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "不明なオプション: $1"
            echo "ヘルプを表示するには: $0 --help"
            exit 1
            ;;
    esac
done

# ========================================
# ヘッダー表示
# ========================================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         OITERUシステム 子機起動スクリプト                ║${NC}"
echo -e "${CYAN}║              (Raspberry Pi用)                            ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 起動モードの確認
if [ "$AUTO_MODE" = false ] && [ "$FIND_SERVER" = false ] && [ -z "$SERVER_HOST" ]; then
    log_error "起動モードが指定されていません"
    echo ""
    echo "以下のいずれかを指定してください:"
    echo "  --host <親機IP>  親機のIPアドレスを指定"
    echo "  --auto           設定ファイルから自動起動"
    echo "  --find-server    親機を自動探知"
    echo ""
    echo "ヘルプ: $0 --help"
    echo ""
    exit 1
fi

# root権限チェック
if [ "$EUID" -ne 0 ]; then
    log_warning "NFCリーダーを使用するにはsudo権限が必要です"
    log_warning "sudo $0 $@ で再実行してください"
fi

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_status "プロジェクトディレクトリ: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ========================================
# ステップ 1: 仮想環境のセットアップ
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 1: Python仮想環境のセットアップ"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

VENV_PATHS=(".venv" "venv" "env" ".env")
VENV_FOUND=""
VENV_PYTHON=""

for path in "${VENV_PATHS[@]}"; do
    activate_script="$PROJECT_DIR/$path/bin/activate"
    python_exe="$PROJECT_DIR/$path/bin/python"
    
    if [ -f "$activate_script" ]; then
        VENV_FOUND="$path"
        VENV_PYTHON="$python_exe"
        log_success "仮想環境を発見: $path"
        break
    fi
done

if [ -z "$VENV_FOUND" ]; then
    log_warning "仮想環境が見つかりません。新規作成します..."
    
    # Pythonのバージョン確認
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Pythonが見つかりません。Pythonをインストールしてください。"
        echo ""
        echo "インストール方法:"
        echo "  sudo apt update && sudo apt install python3 python3-venv python3-pip"
        echo ""
        exit 1
    fi
    
    python_version=$($PYTHON_CMD --version 2>&1)
    log_status "システムPython: $python_version"
    
    # 仮想環境作成
    log_status "仮想環境を作成中: .venv"
    $PYTHON_CMD -m venv .venv
    
    if [ $? -ne 0 ]; then
        log_error "仮想環境の作成に失敗しました"
        log_warning "python3-venvパッケージをインストールしてください:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi
    
    VENV_FOUND=".venv"
    VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
    log_success "仮想環境を作成しました: .venv"
fi

# 仮想環境をアクティベート
ACTIVATE_SCRIPT="$PROJECT_DIR/$VENV_FOUND/bin/activate"
log_status "仮想環境をアクティベート中..."
source "$ACTIVATE_SCRIPT"

# pipのアップグレード
log_status "pipをアップグレード中..."
"$VENV_PYTHON" -m pip install --upgrade pip -q 2>/dev/null

# requirements-client.txtのインストール
REQUIREMENTS_FILE=""
if [ -f "$PROJECT_DIR/requirements-client.txt" ]; then
    REQUIREMENTS_FILE="requirements-client.txt"
elif [ -f "$PROJECT_DIR/requirements.txt" ]; then
    REQUIREMENTS_FILE="requirements.txt"
fi

if [ -n "$REQUIREMENTS_FILE" ]; then
    log_status "依存パッケージをインストール中 ($REQUIREMENTS_FILE)..."
    "$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/$REQUIREMENTS_FILE" -q 2>/dev/null
    log_success "$REQUIREMENTS_FILE インストール完了"
fi

# ========================================
# ステップ 2: NFCリーダーの確認
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 2: ハードウェアの確認"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# USBデバイス確認
if command -v lsusb &> /dev/null; then
    if lsusb | grep -qi "sony\|rc-s380"; then
        log_success "NFCリーダー (Sony RC-S380) を検出しました"
    else
        log_warning "NFCリーダーが見つかりません"
        log_warning "カード読み取り機能が制限されます"
    fi
else
    log_warning "lsusbコマンドがありません。NFCリーダーの確認をスキップします"
fi

# GPIO確認（Raspberry Pi）
if [ -d "/sys/class/gpio" ]; then
    log_success "GPIO利用可能"
else
    log_warning "GPIOが利用できません。モーター制御が制限される可能性があります"
fi

# ========================================
# ステップ 3: 親機への接続テスト
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 3: 親機への接続準備"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -n "$SERVER_HOST" ]; then
    log_status "親機 ($SERVER_HOST:$SERVER_PORT) への接続をテスト中..."
    
    # curlで接続テスト
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 5 "http://$SERVER_HOST:$SERVER_PORT/api/units" > /dev/null 2>&1; then
            log_success "親機への接続に成功しました"
        else
            log_warning "親機への接続に失敗しました"
            log_warning "起動後に再接続を試みます"
        fi
    elif command -v nc &> /dev/null; then
        if nc -z -w5 "$SERVER_HOST" "$SERVER_PORT" 2>/dev/null; then
            log_success "親機への接続に成功しました"
        else
            log_warning "親機への接続に失敗しました"
            log_warning "起動後に再接続を試みます"
        fi
    else
        log_warning "接続テストコマンドがありません。テストをスキップします"
    fi
fi

# ========================================
# ステップ 4: 子機クライアント起動
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 4: 子機クライアント起動"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# unit_client.py を探す
CLIENT_SCRIPT=""
if [ -f "$PROJECT_DIR/unit_client.py" ]; then
    CLIENT_SCRIPT="unit_client.py"
elif [ -f "$PROJECT_DIR/unit.py" ]; then
    CLIENT_SCRIPT="unit.py"
else
    log_error "unit_client.py または unit.py が見つかりません"
    exit 1
fi

# 起動オプション構築
LAUNCH_OPTS=""

if [ "$GUI_MODE" = false ]; then
    LAUNCH_OPTS="$LAUNCH_OPTS --no-gui"
fi

if [ "$AUTO_MODE" = true ]; then
    LAUNCH_OPTS="$LAUNCH_OPTS --auto"
fi

if [ "$FIND_SERVER" = true ]; then
    LAUNCH_OPTS="$LAUNCH_OPTS --find-server"
fi

if [ -n "$SERVER_HOST" ]; then
    LAUNCH_OPTS="$LAUNCH_OPTS --server $SERVER_HOST --port $SERVER_PORT"
fi

if [ -n "$UNIT_ID" ]; then
    LAUNCH_OPTS="$LAUNCH_OPTS --unit-id $UNIT_ID"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  子機クライアント起動情報                ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
if [ -n "$SERVER_HOST" ]; then
    printf "${GREEN}║  親機サーバー : %-38s║${NC}\n" "$SERVER_HOST:$SERVER_PORT"
fi
if [ -n "$UNIT_ID" ]; then
    printf "${GREEN}║  子機ID       : %-38s║${NC}\n" "$UNIT_ID"
fi
if [ "$AUTO_MODE" = true ]; then
    printf "${GREEN}║  モード       : %-38s║${NC}\n" "自動起動"
elif [ "$FIND_SERVER" = true ]; then
    printf "${GREEN}║  モード       : %-38s║${NC}\n" "親機自動探知"
else
    printf "${GREEN}║  モード       : %-38s║${NC}\n" "手動設定"
fi
if [ "$GUI_MODE" = true ]; then
    printf "${GREEN}║  表示         : %-38s║${NC}\n" "GUI"
else
    printf "${GREEN}║  表示         : %-38s║${NC}\n" "CUI"
fi
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log_status "子機クライアントを起動中... (Ctrl+C で停止)"
echo ""

# クライアント起動（sudoで実行）
if [ "$EUID" -eq 0 ]; then
    "$VENV_PYTHON" "$CLIENT_SCRIPT" $LAUNCH_OPTS
else
    sudo "$VENV_PYTHON" "$CLIENT_SCRIPT" $LAUNCH_OPTS
fi
