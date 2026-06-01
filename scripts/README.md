# Scripts ディレクトリ

このディレクトリには、OITERUシステムのセットアップと運用に必要なスクリプトが含まれています。

## 📁 ファイル一覧

### 子機セットアップ

| ファイル名 | 説明 | 対象環境 |
|----------|------|---------|
| `setup_unit_environment.sh` | 子機環境の自動セットアップ | Raspberry Pi (Linux) |
| `setup_unit_environment.ps1` | 子機環境の自動セットアップ | Windows (開発・テスト用) |
| `SETUP_UNIT.md` | 子機セットアップの詳細ガイド | 全環境 |

### 親機/従親機セットアップ

| ファイル名 | 説明 | 対象環境 |
|----------|------|---------|
| `quick_start_parent.sh` | 親機(MySQL標準構成)のクイックスタート | Linux |
| `quick_start_parent.ps1` | 親機(MySQL標準構成)のクイックスタート | Windows |
| `quick_start_sub.sh` | 従親機のクイックスタート | Linux |
| `quick_start_sub.ps1` | 従親機のクイックスタート | Windows |
| `setup_config.sh` | 設定ファイルの対話的作成 | Linux |
| `setup_config.ps1` | 設定ファイルの対話的作成 | Windows |
| `setup_multi_server.sh` | マルチサーバー環境のセットアップ | Linux (Docker) |

### ランチャー (推奨)

| ファイル名 | 説明 | 対象環境 |
|----------|------|---------|
| `launcher.sh` | 統合ランチャー | Linux |
| `launcher.ps1` | 統合ランチャー | Windows |
| `launcher.bat` | 統合ランチャー (バッチ版) | Windows |
| `launcher_gui.py` | GUIランチャー | 全環境 (要Tkinter) |
| `launcher_cui.py` | CUIランチャー | 全環境 |
| `LAUNCHER_README.md` | ランチャーの使い方 | - |
| `QUICKSTART_LAUNCHER.md` | ランチャーのクイックスタート | - |

### データベース関連

| ファイル名 | 説明 | 対象環境 |
|----------|------|---------|
| `open_mysql_port_windows.ps1` | MySQL外部接続設定 | Windows |
| `open_mysql_port_linux.sh` | MySQL外部接続設定 | Linux |
| `check_mysql_port.ps1` | MySQLポート確認 | Windows |

### カードリーダー関連

| ファイル名 | 説明 | 対象環境 |
|----------|------|---------|
| `attach_card_reader.ps1` | カードリーダーをWSL2に接続 | Windows + WSL2 |
| `attach_card_reader.bat` | カードリーダーをWSL2に接続 (バッチ版) | Windows + WSL2 |
| `auto_attach_card_reader.sh` | カードリーダーの自動接続 | Linux |
| `init_card_reader.sh` | NFCカードリーダーの初期化 | Linux |
| `fix_card_reader.ps1` | カードリーダー問題の修正 | Windows |
| `fix_card_reader.bat` | カードリーダー問題の修正 (バッチ版) | Windows |

### 運用スクリプト

| ファイル名 | 説明 | 対象環境 |
|----------|------|---------|
| `start_oiteru.sh` | OITERUサーバーの起動 | Linux |
| `start_oiteru.ps1` | OITERUサーバーの起動 | Windows |
| `start_oiteru_mysql.sh` | MySQL版サーバーの起動 | Linux |
| `start_oiteru_mysql.bat` | MySQL版サーバーの起動 | Windows |
| `start_parent.ps1` | 親機の起動 | Windows |
| `start_sub_parent.sh` | 従親機の起動 | Linux |
| `start_sub_parent.bat` | 従親機の起動 | Windows |
| `start_unit.sh` | 子機の起動 | Linux (Raspberry Pi) |
| `start_unit.bat` | 子機の起動 | Windows (開発用) |
| `start_unit_new.sh` | 子機の起動 (新版) | Linux (Raspberry Pi) |
| `unit_client_watchdog.sh` | 子機の監視・自動再起動 | Linux |
| `test_nfc_in_container.sh` | DockerコンテナでのNFCテスト | Linux (Docker) |

### その他

| ファイル名 | 説明 |
|----------|------|
| `launcher_config.json` | ランチャーの設定ファイル |
| `launcher_utils.py` | ランチャーのユーティリティ関数 |
| `fix_powershell_policy.bat` | PowerShell実行ポリシーの修正 |

## 🚀 使い方

### 1. 子機のセットアップ (Raspberry Pi)

```bash
# スクリプトに実行権限を付与
chmod +x scripts/setup_unit_environment.sh

# セットアップを実行
./scripts/setup_unit_environment.sh

# 詳細はドキュメントを参照
cat scripts/SETUP_UNIT.md
```

### 2. 親機/従親機のセットアップ

#### ランチャーを使用 (推奨)

```bash
# Linux
./scripts/launcher.sh

# Windows PowerShell
.\scripts\launcher.ps1
```

#### 個別スクリプトを使用

```bash
# 親機 (Linux)
./scripts/quick_start_parent.sh

# 親機 (Windows)
.\scripts\quick_start_parent.ps1

# 従親機 (Linux)
./scripts/quick_start_sub.sh
```

## 📝 注意事項

- **Linux/macOS**: スクリプトに実行権限を付与してください (`chmod +x <script>`)
- **Windows**: PowerShellスクリプトは実行ポリシーの設定が必要な場合があります
  - `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
  - または `fix_powershell_policy.bat` を実行
- **Raspberry Pi**: 子機のセットアップには管理者権限 (sudo) が必要です

## 🔗 関連ドキュメント

- [QUICKSTART.md](../取説書/QUICKSTART.md) - システム全体のクイックスタートガイド
- [SETUP_UNIT.md](SETUP_UNIT.md) - 子機セットアップの詳細ガイド
- [LAUNCHER_README.md](LAUNCHER_README.md) - ランチャーの使い方
- [config_templates/README.md](../config_templates/README.md) - 設定ファイルの詳細
