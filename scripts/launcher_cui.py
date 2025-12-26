#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU ランチャー (CUI版 - BIOS風)
=========================================

親機・従親機・子機を簡単に起動できるBIOS風CUIランチャー
"""

import os
import sys
import time
import platform
from pathlib import Path

# ユーティリティモジュールをインポート
from launcher_utils import (
    load_config, save_config,
    detect_venv, create_venv, install_requirements,
    check_docker, check_docker_compose,
    start_server_normal, start_server_venv, start_server_docker,
    get_role_display_name, get_mode_display_name,
    MODE_NORMAL, MODE_VENV, MODE_DOCKER,
    ROLE_PARENT, ROLE_SUB_PARENT, ROLE_UNIT,
    get_system_info, check_port_available,
    detect_card_reader, check_pcscd, start_pcscd,
    attach_usb_to_wsl, initialize_card_reader
)

# ========================================
# ANSI カラーコード
# ========================================
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # 前景色
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # 背景色
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

# Windows向けのANSI対応
if platform.system() == "Windows":
    os.system("")  # ANSIエスケープシーケンスを有効化

# ========================================
# BIOS風UI関数
# ========================================

def clear_screen():
    """画面をクリア"""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def print_header():
    """BIOSヘッダーを表示"""
    print(f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════════════════════╗")
    print("║                      OITELU SYSTEM LAUNCHER v2.0                          ║")
    print("║                      Boot Configuration Utility                           ║")
    print("╚═══════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

def print_footer():
    """BIOSフッターを表示"""
    print(f"\n{Colors.BG_BLUE}{Colors.WHITE}")
    print("─" * 79)
    print("  F1=Help  F2=Setup  F10=Save & Exit  ESC=Exit Without Saving")
    print(f"{Colors.RESET}")

def print_box(title, content, width=75):
    """枠で囲まれたボックスを表示"""
    print(f"\n{Colors.CYAN}┌─ {title} " + "─" * (width - len(title) - 4) + "┐")
    for line in content:
        padding = width - len(line) - 2
        print(f"│ {line}" + " " * padding + "│")
    print("└" + "─" * (width - 2) + "┘" + Colors.RESET)

def print_menu(title, options, selected=0):
    """メニューを表示"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ {title} ═══{Colors.RESET}\n")
    for i, option in enumerate(options):
        if i == selected:
            print(f"  {Colors.BG_WHITE}{Colors.BLACK}► {option}{Colors.RESET}")
        else:
            print(f"    {option}")

def get_input(prompt, default=""):
    """入力を取得"""
    if default:
        user_input = input(f"{Colors.GREEN}{prompt} [{default}]: {Colors.RESET}")
        return user_input if user_input else default
    else:
        return input(f"{Colors.GREEN}{prompt}: {Colors.RESET}")

def pause():
    """一時停止"""
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.RESET}")

def show_loading(message, duration=2):
    """ローディングアニメーション"""
    chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r{Colors.CYAN}{chars[i % len(chars)]} {message}...{Colors.RESET}", end="", flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r{Colors.GREEN}✓ {message}...完了{Colors.RESET}")

# ========================================
# メイン画面
# ========================================

class BIOSLauncher:
    def __init__(self):
        self.config = load_config()
        self.selected_role = self.config.get("last_role", ROLE_PARENT)
        self.selected_mode = self.config.get("last_mode", MODE_NORMAL)
        self.running = True
    
    def main_menu(self):
        """メインメニュー"""
        while self.running:
            clear_screen()
            print_header()
            
            # システム情報
            sys_info = get_system_info()
            print_box("System Information", [
                f"Platform      : {sys_info['platform']}",
                f"Python        : {sys_info['python_version']}",
                f"Hostname      : {sys_info['hostname']}",
                f"Working Dir   : {sys_info['cwd'][:50]}..."
            ])
            
            # 現在の設定
            print_box("Current Configuration", [
                f"Boot Mode     : {get_role_display_name(self.selected_role)}",
                f"Launch Mode   : {get_mode_display_name(self.selected_mode)}",
                f"Server Name   : {self.config.get('server_name', 'N/A')}",
                f"Server Port   : {self.config.get('server_port', 5000)}"
            ])
            
            # メニューオプション
            print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ Main Menu ═══{Colors.RESET}\n")
            print(f"  {Colors.WHITE}1{Colors.RESET} - Select Boot Mode (親機/従親機/子機)")
            print(f"  {Colors.WHITE}2{Colors.RESET} - Select Launch Mode (通常/仮想環境/Docker)")
            print(f"  {Colors.WHITE}3{Colors.RESET} - Environment Check")
            print(f"  {Colors.WHITE}4{Colors.RESET} - Install Dependencies")
            print(f"  {Colors.WHITE}5{Colors.RESET} - Card Reader Setup")
            print(f"  {Colors.WHITE}6{Colors.RESET} - Advanced Settings")
            print(f"  {Colors.WHITE}7{Colors.RESET} - {Colors.GREEN}{Colors.BOLD}► START SYSTEM ◄{Colors.RESET}")
            print(f"  {Colors.WHITE}0{Colors.RESET} - Exit")
            
            print_footer()
            
            choice = get_input("\nSelect option [0-7]", "7")
            
            if choice == "1":
                self.select_boot_mode()
            elif choice == "2":
                self.select_launch_mode()
            elif choice == "3":
                self.environment_check()
            elif choice == "4":
                self.install_dependencies()
            elif choice == "5":
                self.card_reader_setup()
            elif choice == "6":
                self.advanced_settings()
            elif choice == "7":
                self.start_system()
            elif choice == "0":
                self.running = False
            else:
                print(f"{Colors.RED}Invalid option{Colors.RESET}")
                pause()
    
    def select_boot_mode(self):
        """起動モード選択"""
        clear_screen()
        print_header()
        
        print_box("Select Boot Mode", [
            "Choose the system role to launch"
        ])
        
        print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ Boot Mode Selection ═══{Colors.RESET}\n")
        print(f"  {Colors.WHITE}1{Colors.RESET} - 🖥️  Parent Server    (親機 - データベース管理)")
        print(f"  {Colors.WHITE}2{Colors.RESET} - 🔄  Sub Parent Server (従親機 - 外部DB接続)")
        print(f"  {Colors.WHITE}3{Colors.RESET} - 📟  Unit Client       (子機 - NFC + モーター)")
        print(f"  {Colors.WHITE}0{Colors.RESET} - ← Back")
        
        choice = get_input("\nSelect boot mode [0-3]", "1")
        
        if choice == "1":
            self.selected_role = ROLE_PARENT
            print(f"{Colors.GREEN}✓ Parent Server selected{Colors.RESET}")
        elif choice == "2":
            self.selected_role = ROLE_SUB_PARENT
            print(f"{Colors.GREEN}✓ Sub Parent Server selected{Colors.RESET}")
        elif choice == "3":
            self.selected_role = ROLE_UNIT
            print(f"{Colors.GREEN}✓ Unit Client selected{Colors.RESET}")
        elif choice == "0":
            return
        else:
            print(f"{Colors.RED}Invalid option{Colors.RESET}")
        
        pause()
    
    def select_launch_mode(self):
        """実行モード選択"""
        clear_screen()
        print_header()
        
        print_box("Select Launch Mode", [
            "Choose how to execute the system"
        ])
        
        print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ Launch Mode Selection ═══{Colors.RESET}\n")
        print(f"  {Colors.WHITE}1{Colors.RESET} - ⚡ Normal Mode      (直接Python実行)")
        print(f"  {Colors.WHITE}2{Colors.RESET} - 🐍 Virtual Env Mode (仮想環境で実行)")
        print(f"  {Colors.WHITE}3{Colors.RESET} - 🐳 Docker Mode      (Dockerコンテナで実行)")
        print(f"  {Colors.WHITE}0{Colors.RESET} - ← Back")
        
        choice = get_input("\nSelect launch mode [0-3]", "1")
        
        if choice == "1":
            self.selected_mode = MODE_NORMAL
            print(f"{Colors.GREEN}✓ Normal Mode selected{Colors.RESET}")
        elif choice == "2":
            self.selected_mode = MODE_VENV
            print(f"{Colors.GREEN}✓ Virtual Environment Mode selected{Colors.RESET}")
        elif choice == "3":
            self.selected_mode = MODE_DOCKER
            print(f"{Colors.GREEN}✓ Docker Mode selected{Colors.RESET}")
        elif choice == "0":
            return
        else:
            print(f"{Colors.RED}Invalid option{Colors.RESET}")
        
        pause()
    
    def environment_check(self):
        """環境チェック"""
        clear_screen()
        print_header()
        
        print_box("Environment Check", [
            "Checking system environment and dependencies..."
        ])
        
        print()
        
        # Python
        print(f"{Colors.CYAN}[1/5] Python Environment{Colors.RESET}")
        show_loading("Checking Python", 0.5)
        print(f"      Version: {platform.python_version()}")
        
        # 仮想環境
        print(f"\n{Colors.CYAN}[2/5] Virtual Environment{Colors.RESET}")
        show_loading("Detecting venv", 0.5)
        venv_path = detect_venv()
        if venv_path:
            print(f"      {Colors.GREEN}✓ Found: {venv_path}{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}⚠ Not detected{Colors.RESET}")
        
        # Docker
        print(f"\n{Colors.CYAN}[3/5] Docker{Colors.RESET}")
        show_loading("Checking Docker", 0.5)
        docker_ok, docker_msg = check_docker()
        if docker_ok:
            print(f"      {Colors.GREEN}✓ {docker_msg}{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}⚠ {docker_msg}{Colors.RESET}")
        
        # Docker Compose
        print(f"\n{Colors.CYAN}[4/5] Docker Compose{Colors.RESET}")
        show_loading("Checking Docker Compose", 0.5)
        compose_ok, compose_msg = check_docker_compose()
        if compose_ok:
            print(f"      {Colors.GREEN}✓ {compose_msg}{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}⚠ {compose_msg}{Colors.RESET}")
        
        # ポート
        print(f"\n{Colors.CYAN}[5/5] Port Availability{Colors.RESET}")
        show_loading("Checking port", 0.5)
        port = self.config.get("server_port", 5000)
        if check_port_available(port):
            print(f"      {Colors.GREEN}✓ Port {port} is available{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}⚠ Port {port} is in use{Colors.RESET}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}Environment check completed!{Colors.RESET}")
        pause()
    
    def install_dependencies(self):
        """依存パッケージインストール"""
        clear_screen()
        print_header()
        
        print_box("Install Dependencies", [
            "Installing required Python packages from requirements.txt"
        ])
        
        print()
        
        if self.selected_mode == MODE_VENV:
            # 仮想環境を検出または作成
            venv_path = detect_venv()
            if not venv_path:
                print(f"{Colors.YELLOW}Virtual environment not found. Creating...{Colors.RESET}")
                show_loading("Creating venv", 2)
                success, msg = create_venv()
                print(f"      {msg}")
                if not success:
                    pause()
                    return
                venv_path = detect_venv()
            
            print(f"{Colors.GREEN}✓ Virtual environment: {venv_path}{Colors.RESET}")
            print()
            show_loading("Installing packages", 3)
            success, msg = install_requirements(venv_path)
            print(f"      {msg}")
        else:
            # 通常のPython
            show_loading("Installing packages", 3)
            success, msg = install_requirements()
            print(f"      {msg}")
        
        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}Installation completed successfully!{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}Installation failed!{Colors.RESET}")
        
        pause()
    
    def card_reader_setup(self):
        """カードリーダーセットアップ"""
        clear_screen()
        print_header()
        
        print_box("Card Reader Setup", [
            "Setting up NFC card reader for the system"
        ])
        
        print()
        
        # カードリーダーを初期化
        print(f"{Colors.CYAN}[1/3] Detecting card reader...{Colors.RESET}")
        show_loading("Scanning USB devices", 1)
        reader_ok, reader_msg = detect_card_reader()
        
        if reader_ok:
            print(f"      {Colors.GREEN}✓ {reader_msg}{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}⚠ {reader_msg}{Colors.RESET}")
        
        # Windows環境でWSL USBアタッチを試行
        if platform.system() == "Windows":
            print(f"\n{Colors.CYAN}[2/3] Attaching USB to WSL...{Colors.RESET}")
            show_loading("Configuring USB passthrough", 2)
            attach_ok, attach_msg = attach_usb_to_wsl()
            
            if attach_ok:
                print(f"      {Colors.GREEN}✓ {attach_msg}{Colors.RESET}")
            else:
                print(f"      {Colors.YELLOW}⚠ {attach_msg}{Colors.RESET}")
        else:
            attach_ok = True  # Linux環境ではアタッチ不要
        
        # pcscdを起動
        print(f"\n{Colors.CYAN}[3/3] Starting pcscd daemon...{Colors.RESET}")
        show_loading("Initializing PC/SC service", 1)
        pcscd_ok, pcscd_msg = start_pcscd()
        
        if pcscd_ok:
            print(f"      {Colors.GREEN}✓ {pcscd_msg}{Colors.RESET}")
        else:
            print(f"      {Colors.YELLOW}⚠ {pcscd_msg}{Colors.RESET}")
        
        # 総合結果
        print()
        if reader_ok and attach_ok and pcscd_ok:
            print(f"{Colors.GREEN}{Colors.BOLD}═══════════════════════════════════════════════════{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}   Card Reader Setup Completed Successfully!{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}═══════════════════════════════════════════════════{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}{Colors.BOLD}Card Reader Setup completed with warnings.{Colors.RESET}")
            print(f"{Colors.YELLOW}Please check the messages above.{Colors.RESET}")
        
        pause()
    
    def advanced_settings(self):
        """詳細設定"""
        while True:
            clear_screen()
            print_header()
            
            print_box("Advanced Settings", [
                "Modify system configuration"
            ])
            
            print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ Settings Menu ═══{Colors.RESET}\n")
            print(f"  {Colors.WHITE}1{Colors.RESET} - Server Name       : {self.config.get('server_name', 'N/A')}")
            print(f"  {Colors.WHITE}2{Colors.RESET} - Server Location   : {self.config.get('server_location', 'N/A')}")
            print(f"  {Colors.WHITE}3{Colors.RESET} - Server Port       : {self.config.get('server_port', 5000)}")
            print(f"  {Colors.WHITE}4{Colors.RESET} - Parent URL        : {self.config.get('parent_url', 'N/A')}")
            print(f"  {Colors.WHITE}5{Colors.RESET} - Unit Name         : {self.config.get('unit_name', 'N/A')}")
            print(f"  {Colors.WHITE}6{Colors.RESET} - MySQL Settings")
            print(f"  {Colors.WHITE}9{Colors.RESET} - {Colors.GREEN}Save Settings{Colors.RESET}")
            print(f"  {Colors.WHITE}0{Colors.RESET} - ← Back (without saving)")
            
            choice = get_input("\nSelect option [0-9]", "0")
            
            if choice == "1":
                value = get_input("Enter server name", self.config.get('server_name', ''))
                self.config['server_name'] = value
            elif choice == "2":
                value = get_input("Enter server location", self.config.get('server_location', ''))
                self.config['server_location'] = value
            elif choice == "3":
                value = get_input("Enter server port", str(self.config.get('server_port', 5000)))
                try:
                    self.config['server_port'] = int(value)
                except:
                    print(f"{Colors.RED}Invalid port number{Colors.RESET}")
                    pause()
            elif choice == "4":
                value = get_input("Enter parent URL", self.config.get('parent_url', ''))
                self.config['parent_url'] = value
            elif choice == "5":
                value = get_input("Enter unit name", self.config.get('unit_name', ''))
                self.config['unit_name'] = value
            elif choice == "6":
                self.mysql_settings()
            elif choice == "9":
                show_loading("Saving configuration", 1)
                if save_config(self.config):
                    print(f"{Colors.GREEN}✓ Configuration saved successfully{Colors.RESET}")
                else:
                    print(f"{Colors.RED}✗ Failed to save configuration{Colors.RESET}")
                pause()
                break
            elif choice == "0":
                break
            else:
                print(f"{Colors.RED}Invalid option{Colors.RESET}")
                pause()
    
    def mysql_settings(self):
        """MySQL設定"""
        clear_screen()
        print_header()
        
        print_box("MySQL Settings", [
            "Configure MySQL database connection"
        ])
        
        print(f"\n{Colors.CYAN}Current MySQL Configuration:{Colors.RESET}")
        print(f"  Host     : {self.config.get('mysql_host', 'N/A')}")
        print(f"  Port     : {self.config.get('mysql_port', 3306)}")
        print(f"  Database : {self.config.get('mysql_database', 'N/A')}")
        print(f"  User     : {self.config.get('mysql_user', 'N/A')}")
        print()
        
        if get_input("Do you want to change MySQL settings? (y/n)", "n").lower() == "y":
            self.config['mysql_host'] = get_input("MySQL Host", self.config.get('mysql_host', 'localhost'))
            port_str = get_input("MySQL Port", str(self.config.get('mysql_port', 3306)))
            try:
                self.config['mysql_port'] = int(port_str)
            except:
                pass
            self.config['mysql_database'] = get_input("Database Name", self.config.get('mysql_database', 'oiteru'))
            self.config['mysql_user'] = get_input("User Name", self.config.get('mysql_user', 'oiteru_user'))
            self.config['mysql_password'] = get_input("Password", self.config.get('mysql_password', ''))
            
            print(f"\n{Colors.GREEN}✓ MySQL settings updated{Colors.RESET}")
        
        pause()
    
    def start_system(self):
        """システム起動"""
        clear_screen()
        print_header()
        
        role_name = get_role_display_name(self.selected_role)
        mode_name = get_mode_display_name(self.selected_mode)
        
        print_box("System Launch", [
            f"Boot Mode   : {role_name}",
            f"Launch Mode : {mode_name}",
            "",
            "Starting system..."
        ])
        
        print()
        
        try:
            show_loading("Initializing", 1)
            
            if self.selected_mode == MODE_NORMAL:
                process, msg = start_server_normal(self.selected_role, self.config)
                print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
            
            elif self.selected_mode == MODE_VENV:
                venv_path = detect_venv()
                if not venv_path:
                    print(f"{Colors.RED}✗ Virtual environment not found{Colors.RESET}")
                    print(f"{Colors.YELLOW}Please install dependencies first (option 4){Colors.RESET}")
                    pause()
                    return
                process, msg = start_server_venv(self.selected_role, self.config, venv_path)
                print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
            
            elif self.selected_mode == MODE_DOCKER:
                docker_ok, docker_msg = check_docker()
                if not docker_ok:
                    print(f"{Colors.RED}✗ {docker_msg}{Colors.RESET}")
                    pause()
                    return
                
                show_loading("Starting Docker containers", 2)
                process, msg = start_server_docker(self.selected_role, self.config)
                print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
            
            # 設定を保存
            self.config['last_role'] = self.selected_role
            self.config['last_mode'] = self.selected_mode
            save_config(self.config)
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}═══════════════════════════════════════════════════{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}   SYSTEM STARTED SUCCESSFULLY!{Colors.RESET}")
            print(f"{Colors.GREEN}{Colors.BOLD}═══════════════════════════════════════════════════{Colors.RESET}")
            
            if self.selected_role in [ROLE_PARENT, ROLE_SUB_PARENT]:
                port = self.config.get('server_port', 5000)
                print(f"\n{Colors.CYAN}Web Interface: http://localhost:{port}/admin{Colors.RESET}")
            
            print(f"\n{Colors.YELLOW}Press Ctrl+C to stop the system{Colors.RESET}")
            
            if self.selected_mode != MODE_DOCKER and process:
                # プロセスが終了するまで待機
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print(f"\n\n{Colors.YELLOW}Stopping system...{Colors.RESET}")
                    process.terminate()
                    process.wait()
                    print(f"{Colors.GREEN}✓ System stopped{Colors.RESET}")
            
            pause()
            
        except Exception as e:
            print(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
            import traceback
            print(traceback.format_exc())
            pause()

def main():
    launcher = BIOSLauncher()
    try:
        launcher.main_menu()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Launcher interrupted by user{Colors.RESET}")
    except Exception as e:
        print(f"\n\n{Colors.RED}Fatal error: {e}{Colors.RESET}")
        import traceback
        print(traceback.format_exc())
    finally:
        clear_screen()
        print(f"{Colors.CYAN}Thank you for using OITELU System Launcher!{Colors.RESET}\n")

if __name__ == "__main__":
    main()
