#!/bin/bash
###############################################################################
# OITERUシステム - 子機環境セットアップスクリプト
# Raspberry Pi上でこのスクリプトを実行して、子機の動作環境を準備します
###############################################################################

set -e  # エラーが発生したら停止

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  OITERUシステム - 子機環境セットアップ"
echo "=========================================="
echo ""

# --- 1. システムパッケージの更新 ---
echo "📦 [1/6] システムパッケージを更新中..."
sudo apt-get update
sudo apt-get upgrade -y

# --- 2. 必要なシステムパッケージのインストール ---
echo ""
echo "🔧 [2/6] 必要なシステムパッケージをインストール中..."
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-tk \
    libusb-1.0-0-dev \
    libnfc-dev \
    pcscd \
    i2c-tools \
    git \
    tmux

# --- 3. I2Cの有効化 ---
echo ""
echo "🔌 [3/6] I2Cインターフェースを有効化中..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=i2c_arm=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "I2Cを有効化しています..."
    # Raspberry Pi OS Bookworm以降
    if [ -f /boot/firmware/config.txt ]; then
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/firmware/config.txt
    # 旧バージョン
    elif [ -f /boot/config.txt ]; then
        echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    fi
    
    # i2cモジュールを自動読み込み
    if ! grep -q "^i2c-dev" /etc/modules; then
        echo "i2c-dev" | sudo tee -a /etc/modules
    fi
    
    # ユーザーをi2cグループに追加
    sudo usermod -aG i2c $USER
    echo "✓ I2Cを有効化しました（再起動後に有効になります）"
else
    echo "✓ I2Cは既に有効です"
fi

# --- 4. Python仮想環境の作成 ---
echo ""
echo "🐍 [4/6] Python仮想環境を作成中..."
cd "$PROJECT_ROOT"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ 仮想環境 'venv' を作成しました"
else
    echo "✓ 仮想環境は既に存在します"
fi

# --- 5. Pythonパッケージのインストール ---
echo ""
echo "📚 [5/6] Pythonパッケージをインストール中..."
source venv/bin/activate

# pipを最新版に更新
pip install --upgrade pip setuptools wheel

# 子機用パッケージをインストール
if [ -f "docker/requirements-client.txt" ]; then
    pip install -r docker/requirements-client.txt
    echo "✓ 子機用パッケージをインストールしました"
else
    echo "⚠️  requirements-client.txt が見つかりません"
fi

# --- 6. 設定ファイルの確認 ---
echo ""
echo "⚙️  [6/6] 設定ファイルを確認中..."

if [ ! -f "config.json" ]; then
    if [ -f "config_templates/config_unit.template.json" ]; then
        cp config_templates/config_unit.template.json config.json
        echo "✓ テンプレートからconfig.jsonを作成しました"
        echo ""
        echo "⚠️  重要: config.jsonを編集して、以下を設定してください:"
        echo "   - SERVER_URL: 親機のURL"
        echo "   - UNIT_NAME: この子機の名前"
        echo "   - UNIT_PASSWORD: この子機のパスワード"
    else
        echo "⚠️  config.jsonとテンプレートが見つかりません"
    fi
else
    echo "✓ config.jsonは既に存在します"
fi

# --- 完了メッセージ ---
echo ""
echo "=========================================="
echo "  ✅ セットアップ完了！"
echo "=========================================="
echo ""
echo "📝 次のステップ:"
echo ""
echo "1. config.jsonを編集して設定を完了してください:"
echo "   nano config.json"
echo ""
echo "2. I2Cを有効化した場合は、システムを再起動してください:"
echo "   sudo reboot"
echo ""
echo "3. 子機を起動してください:"
echo "   source venv/bin/activate"
echo "   python unit.py"
echo ""
echo "または、tmuxセッションで起動:"
echo "   tmux new-session -d -s oiteru 'source venv/bin/activate && python unit.py'"
echo "   tmux attach -t oiteru  # ログ確認"
echo ""
echo "=========================================="
