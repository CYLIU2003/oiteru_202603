#!/bin/bash

# ========================================
# Linux Firewall - MySQLポート3306を開くスクリプト
# ========================================
# 
# このスクリプトは、LinuxファイアウォールでポートMySQL（3306）を開きます。
# sudo権限で実行する必要があります。
#
# 【使用方法】
# sudo bash scripts/open_mysql_port_linux.sh
#
# ========================================

echo "========================================"
echo "  Linux Firewall - MySQL Port 3306"
echo "========================================"
echo ""

# root権限チェック
if [ "$EUID" -ne 0 ]; then 
    echo "[エラー] このスクリプトはroot権限で実行する必要があります。"
    echo ""
    echo "以下のコマンドで実行してください:"
    echo "  sudo bash $0"
    exit 1
fi

echo "[OK] root権限で実行されています。"
echo ""

# ファイアウォールの種類を検出
echo "ファイアウォールの種類を検出中..."

if command -v ufw >/dev/null 2>&1; then
    FIREWALL="ufw"
    echo "[検出] UFW (Ubuntu/Debian)"
elif command -v firewall-cmd >/dev/null 2>&1; then
    FIREWALL="firewalld"
    echo "[検出] FirewallD (CentOS/RHEL/Fedora)"
elif command -v iptables >/dev/null 2>&1; then
    FIREWALL="iptables"
    echo "[検出] iptables"
else
    echo "[警告] ファイアウォールが検出されませんでした。"
    echo "ポート3306は既に開いている可能性があります。"
    FIREWALL="none"
fi

echo ""

# ========================================
# UFW (Ubuntu/Debian)
# ========================================
if [ "$FIREWALL" = "ufw" ]; then
    echo "UFWでポート3306を開いています..."
    
    # UFWを有効化（既に有効な場合はスキップ）
    ufw --force enable
    
    # ポート3306を開く（TCP）
    ufw allow 3306/tcp comment 'OITELU MySQL Server'
    
    # 特定のIPアドレスからのみ許可する場合（オプション）
    # ufw allow from 192.168.1.0/24 to any port 3306 proto tcp comment 'OITELU MySQL Server'
    
    echo ""
    echo "[OK] UFWでポート3306を開きました。"
    echo ""
    echo "現在のUFWステータス:"
    ufw status numbered | grep 3306
    
# ========================================
# FirewallD (CentOS/RHEL/Fedora)
# ========================================
elif [ "$FIREWALL" = "firewalld" ]; then
    echo "FirewallDでポート3306を開いています..."
    
    # FirewallDを起動（既に起動している場合はスキップ）
    systemctl start firewalld
    systemctl enable firewalld
    
    # ポート3306を開く（恒久的）
    firewall-cmd --permanent --add-port=3306/tcp
    firewall-cmd --permanent --add-service=mysql
    
    # 特定のIPアドレスからのみ許可する場合（オプション）
    # firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.1.0/24" port protocol="tcp" port="3306" accept'
    
    # 設定を再読み込み
    firewall-cmd --reload
    
    echo ""
    echo "[OK] FirewallDでポート3306を開きました。"
    echo ""
    echo "現在のFirewallDステータス:"
    firewall-cmd --list-ports
    firewall-cmd --list-services | grep mysql
    
# ========================================
# iptables
# ========================================
elif [ "$FIREWALL" = "iptables" ]; then
    echo "iptablesでポート3306を開いています..."
    
    # 既存のルールを確認
    if iptables -C INPUT -p tcp --dport 3306 -j ACCEPT 2>/dev/null; then
        echo "[情報] ポート3306は既に開いています。"
    else
        # ポート3306を開く
        iptables -I INPUT -p tcp --dport 3306 -j ACCEPT
        echo "[OK] iptablesでポート3306を開きました。"
    fi
    
    # 設定を永続化
    if command -v iptables-save >/dev/null 2>&1; then
        if [ -f /etc/sysconfig/iptables ]; then
            iptables-save > /etc/sysconfig/iptables
            echo "[OK] iptables設定を保存しました。(/etc/sysconfig/iptables)"
        elif [ -f /etc/iptables/rules.v4 ]; then
            iptables-save > /etc/iptables/rules.v4
            echo "[OK] iptables設定を保存しました。(/etc/iptables/rules.v4)"
        else
            echo "[警告] iptables設定の永続化場所が不明です。再起動後に設定が失われる可能性があります。"
        fi
    fi
    
    echo ""
    echo "現在のiptablesルール:"
    iptables -L INPUT -n --line-numbers | grep 3306
fi

echo ""
echo "========================================"
echo "  設定が完了しました！"
echo "========================================"
echo ""

# ========================================
# MySQL接続テスト
# ========================================
echo "[次のステップ]"
echo "1. MySQLが起動していることを確認:"
echo "   docker ps | grep mysql"
echo ""
echo "2. 外部から接続をテスト（クライアント側で実行）:"
echo "   mysql -h <このサーバーのIP> -u oiteru_user -p"
echo ""
echo "3. ポートが開いていることを確認（クライアント側で実行）:"
echo "   telnet <このサーバーのIP> 3306"
echo "   または"
echo "   nc -zv <このサーバーのIP> 3306"
echo ""

# ========================================
# セキュリティに関する注意事項
# ========================================
echo "========================================" 
echo "[セキュリティに関する注意]"
echo "========================================"
echo ""
echo "ポート3306を全てのIPアドレスに開放すると、セキュリティリスクがあります。"
echo ""
echo "特定のIPアドレスからのみ接続を許可する方法:"
echo ""
if [ "$FIREWALL" = "ufw" ]; then
    echo "  sudo ufw delete allow 3306/tcp"
    echo "  sudo ufw allow from 192.168.1.100 to any port 3306 proto tcp"
    echo ""
elif [ "$FIREWALL" = "firewalld" ]; then
    echo "  sudo firewall-cmd --permanent --remove-port=3306/tcp"
    echo "  sudo firewall-cmd --permanent --add-rich-rule='rule family=\"ipv4\" source address=\"192.168.1.100\" port protocol=\"tcp\" port=\"3306\" accept'"
    echo "  sudo firewall-cmd --reload"
    echo ""
elif [ "$FIREWALL" = "iptables" ]; then
    echo "  sudo iptables -D INPUT -p tcp --dport 3306 -j ACCEPT"
    echo "  sudo iptables -I INPUT -p tcp -s 192.168.1.100 --dport 3306 -j ACCEPT"
    echo ""
fi

echo "詳細は ADVANCED.md の「セキュリティ設定」セクションを参照してください。"
echo ""
