# OITELU ランチャーシステム - 変更履歴

## 📅 2025年12月26日 - Docker化されたMySQLへの対応

### 🔄 変更内容

#### launcher_utils.py
- **Docker起動時のMySQL対応を改善**
  - 親機でMySQLを選択した場合、`docker-compose.mysql.yml` を自動使用
  - DockerコンテナのMySQLホスト名を `oiteru_mysql` に設定
  - 従親機は引き続き外部MySQL接続用の設定を使用
- **デフォルトパスワードの設定**
  - MySQLのデフォルトパスワードを `oiteru_password_2025` に統一
  - 通常モード、仮想環境モード、Dockerモード全てで一貫性を確保

#### ドキュメント更新
- **LAUNCHER_README.md**
  - Docker化されたMySQLデータベースの使用方法を詳細に追加
  - 親機（MySQL + Docker）の起動手順を明記
  - 従親機から親機のMySQLへの接続方法を追加
  - 通常モード・仮想環境モードでのMySQL接続例を追加
- **QUICKSTART_LAUNCHER.md**
  - MySQL使用時の推奨構成を追加
  - 従親機を別マシンで起動する手順を明記
  - Docker化されたMySQLへの接続方法を説明

### 💡 使い方

#### 親機でDocker + MySQLを使う
1. ランチャーで「親機」を選択
2. 詳細設定で `db_type` を `mysql` に変更
3. 「Dockerモード」を選択
4. 起動 → MySQLコンテナとFlaskサーバーが連携起動

#### 従親機で親機のMySQLに接続
1. ランチャーで「従親機」を選択
2. 詳細設定で親機のIPアドレスを `mysql_host` に設定
3. 起動モード（通常/仮想環境/Docker）を選択
4. 起動 → 親機のMySQLに接続

---

## 📅 2025年12月26日 - 統合ランチャーシステム完成

### 🎉 新規作成ファイル

#### scriptsフォルダに追加されたファイル

1. **launcher_utils.py**
   - 共通ユーティリティモジュール
   - 仮想環境の自動検出・作成
   - Docker環境チェック
   - **カードリーダー管理機能（新機能）**
     - NFCカードリーダーの自動検出
     - Windows WSL環境でのUSB自動アタッチ
     - pcscdデーモンの自動起動

2. **launcher_gui.py**
   - tkinterベースのGUIランチャー
   - リアルタイムターミナル表示
   - 詳細設定ダイアログ
   - **カードリーダー設定ボタン（新機能）**

3. **launcher_cui.py**
   - BIOS風CUIランチャー
   - ANSIカラー対応
   - **カードリーダーセットアップメニュー（新機能）**

4. **launcher_config.json**
   - ランチャー設定ファイル
   - サーバー名、MySQL設定、子機設定など

5. **launcher.bat** / **launcher.ps1** / **launcher.sh**
   - Windows/Linux対応の起動スクリプト

6. **LAUNCHER_README.md**
   - 詳細なドキュメント

7. **QUICKSTART_LAUNCHER.md**
   - クイックスタートガイド

### ✨ 主な機能

#### 起動モード
- 🖥️ **親機** - データベース管理サーバー
- 🔄 **従親機** - 外部MySQL接続サーバー
- 📟 **子機** - NFC + モーター制御

#### 実行方法
- ⚡ **通常モード** - 直接Python実行
- 🐍 **仮想環境モード** - .venv内で実行
- 🐳 **Dockerモード** - コンテナで実行

#### 便利機能
- ✅ 仮想環境の自動検出・作成
- ✅ 依存パッケージの自動インストール
- ✅ 環境チェック（Python、Docker、ポート等）
- ✅ 設定の永続化
- ✅ **カードリーダー自動セットアップ（新機能）**
  - NFCカードリーダーの検出
  - WSL環境でのUSB自動アタッチ
  - pcscdの自動起動

### 💳 カードリーダー対応（重要な追加機能）

親機・従親機でもNFCカードリーダーを使用できるように、以下の機能を追加：

#### 追加された関数（launcher_utils.py）

```python
detect_card_reader()              # カードリーダーを検出
check_pcscd()                     # pcscdの起動状態確認
start_pcscd()                     # pcscdを起動
attach_usb_to_wsl(bus_id)        # WSL環境でUSBアタッチ（Windows専用）
initialize_card_reader()          # カードリーダーを初期化
```

#### GUI版の追加機能
- 「💳 カードリーダー設定」ボタンを追加
- セットアップ進行状況をログにリアルタイム表示

#### CUI版の追加機能
- メインメニューに「5 - Card Reader Setup」を追加
- 3段階のセットアップ表示（検出→アタッチ→pcscd起動）

### 🔧 技術的な改善

1. **パス管理の改善**
   - scriptsフォルダに配置しても正しく動作
   - `get_project_root()` 関数でプロジェクトルートを自動検出

2. **エラーハンドリング**
   - すべての外部コマンドでタイムアウト設定
   - 詳細なエラーメッセージ表示

3. **クロスプラットフォーム対応**
   - Windows/Linux/Macで動作
   - プラットフォーム固有の機能を自動判別

### 📝 使用方法

#### 基本的な起動

```bash
# Windows
cd scripts
launcher.bat

# Linux/Mac
cd scripts
./launcher.sh
```

#### カードリーダーのセットアップ

1. ランチャーを起動
2. GUI版：「💳 カードリーダー設定」をクリック
3. CUI版：メニューから「5」を選択

### 🎯 今後の展開

このランチャーシステムにより：
- 初心者でも簡単にシステムを起動できる
- カードリーダーのセットアップが自動化される
- 親機・従親機・子機を統一的に管理できる
- 環境の違いを意識せずに利用できる

---

**開発日**: 2025年12月26日  
**バージョン**: 2.0  
**場所**: scripts/ フォルダ
