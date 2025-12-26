# OITELU ランチャー - クイックスタート

## 📌 はじめに

OITELU システムランチャーをscriptsフォルダに配置しました。
親機・従親機・子機を簡単に起動できます。

## 🚀 すぐに使う

### Windows

1. エクスプローラーで `scripts` フォルダを開く
2. `launcher.bat` をダブルクリック
3. GUI版またはCUI版を選択
4. 起動モード（親機/従親機/子機）を選択
5. 「起動」をクリック

### 親機でカードリーダーを使う場合

1. ランチャーを起動
2. **GUI版**: `💳 カードリーダー設定` ボタンをクリック
3. **CUI版**: メニューから `5 - Card Reader Setup` を選択
4. 自動的にセットアップが完了します

## 📋 新機能

### ✨ カードリーダー自動セットアップ

親機・従親機でもNFCカードリーダーを使用する場合、ランチャーから簡単にセットアップできるようになりました。

**対応機能:**
- ✅ NFCカードリーダーの自動検出
- ✅ Windows環境でのWSL自動アタッチ（usbipdを使用）
- ✅ pcscdデーモンの自動起動
- ✅ セットアップ状態のリアルタイム表示

### 🎯 3つの起動モード

1. **親機**: データベース管理サーバー（SQLite/MySQL対応）
2. **従親機**: 外部MySQL接続サーバー
3. **子機**: NFC + モーター制御

### 🐍 3つの実行方法

1. **通常モード**: システムのPythonで直接実行
2. **仮想環境モード**: .venv内で実行（パッケージ分離）
3. **Dockerモード**: コンテナで実行（完全分離）

## 🔧 必要な環境

### すべての環境
- Python 3.8 以上

### カードリーダーを使う場合（親機/従親機）

**Windows + WSL:**
```powershell
# usbipdをインストール
winget install usbipd
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install pcscd pcsc-tools

# Fedora
sudo dnf install pcsc-lite pcsc-tools
```

## 📖 詳しい使い方

`LAUNCHER_README.md` を参照してください。

---

**OITELU System Launcher**  
親機・従親機・子機の統合起動ソリューション
