#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU ランチャー (GUI版)
=========================================

親機・従親機・子機を簡単に起動できるGUIランチャー
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import sys
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

class OITELULauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("OITELU ランチャー")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 設定をロード
        self.config = load_config()
        
        # プロセス管理
        self.current_process = None
        self.log_queue = queue.Queue()
        
        # UIを構築
        self.build_ui()
        
        # ログ更新のためのタイマー
        self.update_log()
        
    def build_ui(self):
        """UIを構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # ========================================
        # タイトル
        # ========================================
        title_label = ttk.Label(
            main_frame,
            text="OITELU システム起動ランチャー",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # ========================================
        # ロール選択
        # ========================================
        role_frame = ttk.LabelFrame(main_frame, text="起動モード", padding="10")
        role_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.role_var = tk.StringVar(value=self.config.get("last_role", ROLE_PARENT))
        
        ttk.Radiobutton(
            role_frame,
            text="🖥️ 親機 (データベース管理サーバー)",
            variable=self.role_var,
            value=ROLE_PARENT,
            command=self.on_role_changed
        ).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        ttk.Radiobutton(
            role_frame,
            text="🔄 従親機 (外部DB接続サーバー)",
            variable=self.role_var,
            value=ROLE_SUB_PARENT,
            command=self.on_role_changed
        ).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Radiobutton(
            role_frame,
            text="📟 子機 (NFC + モーター制御)",
            variable=self.role_var,
            value=ROLE_UNIT,
            command=self.on_role_changed
        ).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # ========================================
        # 実行モード選択
        # ========================================
        mode_frame = ttk.LabelFrame(main_frame, text="実行方法", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.mode_var = tk.StringVar(value=self.config.get("last_mode", MODE_NORMAL))
        
        ttk.Radiobutton(
            mode_frame,
            text="⚡ 通常モード (直接実行)",
            variable=self.mode_var,
            value=MODE_NORMAL
        ).grid(row=0, column=0, sticky=tk.W, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🐍 仮想環境モード",
            variable=self.mode_var,
            value=MODE_VENV
        ).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🐳 Docker モード",
            variable=self.mode_var,
            value=MODE_DOCKER
        ).grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # ========================================
        # 設定ボタン
        # ========================================
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        ttk.Button(
            button_frame,
            text="⚙️ 詳細設定",
            command=self.open_settings,
            width=15
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame,
            text="🔍 環境チェック",
            command=self.check_environment,
            width=15
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            button_frame,
            text="📦 依存関係インストール",
            command=self.install_dependencies,
            width=20
        ).grid(row=0, column=2, padx=5)
        
        ttk.Button(
            button_frame,
            text="💳 カードリーダー設定",
            command=self.setup_card_reader,
            width=20
        ).grid(row=0, column=3, padx=5)
        
        # ========================================
        # 起動・停止ボタン
        # ========================================
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(
            control_frame,
            text="▶️ 起動",
            command=self.start_server,
            width=20,
            style="Accent.TButton"
        )
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(
            control_frame,
            text="⏹️ 停止",
            command=self.stop_server,
            width=20,
            state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # ========================================
        # ログエリア（ターミナル）
        # ========================================
        log_frame = ttk.LabelFrame(main_frame, text="📋 ターミナル出力", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=20,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#00ff00",
            insertbackground="white"
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # クリアボタン
        ttk.Button(
            log_frame,
            text="🗑️ ログクリア",
            command=self.clear_log,
            width=15
        ).grid(row=1, column=0, pady=5)
        
        # ========================================
        # ステータスバー
        # ========================================
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 初期ログ
        self.log("OITELU ランチャーを起動しました")
        self.log(f"システム情報: {get_system_info()}")
    
    def on_role_changed(self):
        """ロール変更時の処理"""
        role = self.role_var.get()
        role_name = get_role_display_name(role)
        self.log(f"起動モードを '{role_name}' に変更しました")
    
    def log(self, message):
        """ログに追加"""
        self.log_queue.put(message)
    
    def update_log(self):
        """ログを更新"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        
        # プロセスの出力を読み取り
        if self.current_process:
            try:
                # stdoutから読み取り
                if self.current_process.stdout:
                    line = self.current_process.stdout.readline()
                    if line:
                        self.log_text.insert(tk.END, line.decode('utf-8', errors='ignore'))
                        self.log_text.see(tk.END)
                
                # プロセスが終了したか確認
                if self.current_process.poll() is not None:
                    self.log("プロセスが終了しました")
                    self.current_process = None
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
                    self.status_var.set("停止")
            except Exception as e:
                pass
        
        # 100ms後に再度実行
        self.root.after(100, self.update_log)
    
    def clear_log(self):
        """ログをクリア"""
        self.log_text.delete(1.0, tk.END)
        self.log("ログをクリアしました")
    
    def check_environment(self):
        """環境をチェック"""
        self.log("=" * 50)
        self.log("環境チェックを開始します...")
        self.log("=" * 50)
        
        # Python環境
        import sys
        self.log(f"✓ Python: {sys.version}")
        
        # 仮想環境
        venv_path = detect_venv()
        if venv_path:
            self.log(f"✓ 仮想環境: {venv_path}")
        else:
            self.log("⚠ 仮想環境: 未検出")
        
        # Docker
        docker_ok, docker_msg = check_docker()
        if docker_ok:
            self.log(f"✓ Docker: {docker_msg}")
            compose_ok, compose_msg = check_docker_compose()
            if compose_ok:
                self.log(f"✓ Docker Compose: {compose_msg}")
            else:
                self.log(f"⚠ Docker Compose: {compose_msg}")
        else:
            self.log(f"⚠ Docker: {docker_msg}")
        
        # ポート確認
        port = self.config.get("server_port", 5000)
        if check_port_available(port):
            self.log(f"✓ ポート {port}: 利用可能")
        else:
            self.log(f"⚠ ポート {port}: 使用中")
        
        self.log("=" * 50)
        self.log("環境チェック完了")
        self.log("=" * 50)
    
    def setup_card_reader(self):
        """カードリーダーをセットアップ"""
        self.log("=" * 50)
        self.log("カードリーダーセットアップを開始します...")
        self.log("=" * 50)
        
        # カードリーダーを初期化
        success, msg = initialize_card_reader(auto_attach_wsl=True)
        
        for line in msg.split('\n'):
            self.log(line)
        
        self.log("=" * 50)
        
        if success:
            messagebox.showinfo("成功", "カードリーダーのセットアップが完了しました")
        else:
            messagebox.showwarning("警告", "カードリーダーのセットアップに問題がありました\n詳細はログを確認してください")
    
    def install_dependencies(self):
        """依存パッケージをインストール"""
        self.log("=" * 50)
        self.log("依存パッケージをインストールします...")
        
        mode = self.mode_var.get()
        
        if mode == MODE_VENV:
            # 仮想環境を検出または作成
            venv_path = detect_venv()
            if not venv_path:
                self.log("仮想環境が見つかりません。作成します...")
                success, msg = create_venv()
                self.log(msg)
                if not success:
                    self.log("=" * 50)
                    return
                venv_path = detect_venv()
            
            self.log(f"仮想環境: {venv_path}")
            success, msg = install_requirements(venv_path)
            self.log(msg)
        else:
            # 通常のPythonでインストール
            success, msg = install_requirements()
            self.log(msg)
        
        self.log("=" * 50)
    
    def start_server(self):
        """サーバーを起動"""
        role = self.role_var.get()
        mode = self.mode_var.get()
        
        self.log("=" * 50)
        self.log(f"起動中: {get_role_display_name(role)} ({get_mode_display_name(mode)})")
        self.log("=" * 50)
        
        try:
            if mode == MODE_NORMAL:
                process, msg = start_server_normal(role, self.config)
                self.current_process = process
            
            elif mode == MODE_VENV:
                venv_path = detect_venv()
                if not venv_path:
                    self.log("エラー: 仮想環境が見つかりません")
                    self.log("先に「📦 依存関係インストール」を実行してください")
                    self.log("=" * 50)
                    return
                process, msg = start_server_venv(role, self.config, venv_path)
                self.current_process = process
            
            elif mode == MODE_DOCKER:
                # Dockerチェック
                docker_ok, docker_msg = check_docker()
                if not docker_ok:
                    self.log(f"エラー: {docker_msg}")
                    self.log("=" * 50)
                    return
                
                process, msg = start_server_docker(role, self.config)
                self.current_process = process
            
            self.log(msg)
            
            # 設定を保存
            self.config["last_role"] = role
            self.config["last_mode"] = mode
            save_config(self.config)
            
            # ボタン状態を更新
            if mode != MODE_DOCKER:
                self.start_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.status_var.set("実行中")
            else:
                self.status_var.set("Dockerで実行中")
            
        except Exception as e:
            self.log(f"エラー: {e}")
            import traceback
            self.log(traceback.format_exc())
        
        self.log("=" * 50)
    
    def stop_server(self):
        """サーバーを停止"""
        if self.current_process:
            self.log("サーバーを停止しています...")
            self.current_process.terminate()
            self.current_process.wait()
            self.current_process = None
            
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_var.set("停止")
            self.log("サーバーを停止しました")
    
    def open_settings(self):
        """設定ダイアログを開く"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("詳細設定")
        settings_window.geometry("500x600")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # タブ
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ========================================
        # 基本設定タブ
        # ========================================
        basic_frame = ttk.Frame(notebook, padding="10")
        notebook.add(basic_frame, text="基本設定")
        
        # サーバー名
        ttk.Label(basic_frame, text="サーバー名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        server_name_var = tk.StringVar(value=self.config.get("server_name", ""))
        ttk.Entry(basic_frame, textvariable=server_name_var, width=40).grid(row=0, column=1, pady=5)
        
        # サーバー設置場所
        ttk.Label(basic_frame, text="設置場所:").grid(row=1, column=0, sticky=tk.W, pady=5)
        server_location_var = tk.StringVar(value=self.config.get("server_location", ""))
        ttk.Entry(basic_frame, textvariable=server_location_var, width=40).grid(row=1, column=1, pady=5)
        
        # ポート番号
        ttk.Label(basic_frame, text="ポート番号:").grid(row=2, column=0, sticky=tk.W, pady=5)
        server_port_var = tk.IntVar(value=self.config.get("server_port", 5000))
        ttk.Entry(basic_frame, textvariable=server_port_var, width=40).grid(row=2, column=1, pady=5)
        
        # ========================================
        # MySQL設定タブ
        # ========================================
        mysql_frame = ttk.Frame(notebook, padding="10")
        notebook.add(mysql_frame, text="MySQL設定")
        
        ttk.Label(mysql_frame, text="ホスト:").grid(row=0, column=0, sticky=tk.W, pady=5)
        mysql_host_var = tk.StringVar(value=self.config.get("mysql_host", ""))
        ttk.Entry(mysql_frame, textvariable=mysql_host_var, width=40).grid(row=0, column=1, pady=5)
        
        ttk.Label(mysql_frame, text="ポート:").grid(row=1, column=0, sticky=tk.W, pady=5)
        mysql_port_var = tk.IntVar(value=self.config.get("mysql_port", 3306))
        ttk.Entry(mysql_frame, textvariable=mysql_port_var, width=40).grid(row=1, column=1, pady=5)
        
        ttk.Label(mysql_frame, text="データベース名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        mysql_db_var = tk.StringVar(value=self.config.get("mysql_database", ""))
        ttk.Entry(mysql_frame, textvariable=mysql_db_var, width=40).grid(row=2, column=1, pady=5)
        
        ttk.Label(mysql_frame, text="ユーザー名:").grid(row=3, column=0, sticky=tk.W, pady=5)
        mysql_user_var = tk.StringVar(value=self.config.get("mysql_user", ""))
        ttk.Entry(mysql_frame, textvariable=mysql_user_var, width=40).grid(row=3, column=1, pady=5)
        
        ttk.Label(mysql_frame, text="パスワード:").grid(row=4, column=0, sticky=tk.W, pady=5)
        mysql_pass_var = tk.StringVar(value=self.config.get("mysql_password", ""))
        ttk.Entry(mysql_frame, textvariable=mysql_pass_var, width=40, show="*").grid(row=4, column=1, pady=5)
        
        # ========================================
        # 子機設定タブ
        # ========================================
        unit_frame = ttk.Frame(notebook, padding="10")
        notebook.add(unit_frame, text="子機設定")
        
        ttk.Label(unit_frame, text="親機URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        parent_url_var = tk.StringVar(value=self.config.get("parent_url", ""))
        ttk.Entry(unit_frame, textvariable=parent_url_var, width=40).grid(row=0, column=1, pady=5)
        
        ttk.Label(unit_frame, text="子機名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        unit_name_var = tk.StringVar(value=self.config.get("unit_name", ""))
        ttk.Entry(unit_frame, textvariable=unit_name_var, width=40).grid(row=1, column=1, pady=5)
        
        ttk.Label(unit_frame, text="パスワード:").grid(row=2, column=0, sticky=tk.W, pady=5)
        unit_pass_var = tk.StringVar(value=self.config.get("unit_password", ""))
        ttk.Entry(unit_frame, textvariable=unit_pass_var, width=40, show="*").grid(row=2, column=1, pady=5)
        
        # ========================================
        # 保存・キャンセルボタン
        # ========================================
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(side=tk.BOTTOM, pady=10)
        
        def save_settings():
            self.config["server_name"] = server_name_var.get()
            self.config["server_location"] = server_location_var.get()
            self.config["server_port"] = server_port_var.get()
            self.config["mysql_host"] = mysql_host_var.get()
            self.config["mysql_port"] = mysql_port_var.get()
            self.config["mysql_database"] = mysql_db_var.get()
            self.config["mysql_user"] = mysql_user_var.get()
            self.config["mysql_password"] = mysql_pass_var.get()
            self.config["parent_url"] = parent_url_var.get()
            self.config["unit_name"] = unit_name_var.get()
            self.config["unit_password"] = unit_pass_var.get()
            
            if save_config(self.config):
                self.log("設定を保存しました")
                messagebox.showinfo("成功", "設定を保存しました")
                settings_window.destroy()
            else:
                messagebox.showerror("エラー", "設定の保存に失敗しました")
        
        ttk.Button(button_frame, text="💾 保存", command=save_settings, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ キャンセル", command=settings_window.destroy, width=15).pack(side=tk.LEFT, padx=5)

def main():
    root = tk.Tk()
    app = OITELULauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
