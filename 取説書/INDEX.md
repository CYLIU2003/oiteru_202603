# 📖 OITELU システム ドキュメント索引

**〜 NFCカードで「お菓子」を管理するスマートIoTシステム 完全ガイド 〜**

このフォルダには、OITELUシステムに関するすべてのドキュメントが含まれています。

---

## 📚 ドキュメント一覧

### 🚀 クイックスタート

初めての方はこちらから:

| ドキュメント | 説明 |
|------------|------|
| [QUICKSTART.md](./QUICKSTART.md) | **最速で始める**。30分でシステム構築 |
| [STARTUP_GUIDE.md](./STARTUP_GUIDE.md) | **起動スクリプト完全ガイド**。自動カードリーダーアタッチの仕組み |
| [README.md](./README.md) | システム全体の概要と初心者向けガイド |

---

### 🔧 セットアップ・設定

システムの構築と設定:

| ドキュメント | 説明 |
|------------|------|
| [MANUAL.md](./MANUAL.md) | 詳細なセットアップマニュアル |
| [IMPLEMENTATION.md](./IMPLEMENTATION.md) | システムの実装詳細とアーキテクチャ |
| [DOCKER_UNIT.md](./DOCKER_UNIT.md) | Docker環境での子機（ユニット）構築ガイド |
| [NFC_DOCKER_GUIDE.md](./NFC_DOCKER_GUIDE.md) | Docker環境でのNFC/カードリーダー設定 |
| [MYSQL_MIGRATION.md](./MYSQL_MIGRATION.md) | **MySQL移行ガイド**。複数デバイス対応のデータベース構築 |
| [REMOTE_ACCESS.md](./REMOTE_ACCESS.md) | リモートアクセス設定（Tailscale VPN） |

---

### 🐛 トラブルシューティング

問題が発生したらこちら:

| ドキュメント | 説明 |
|------------|------|
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | **総合トラブルシューティング**。よくある問題と解決策 |
| [CARD_READER_FIX.md](./CARD_READER_FIX.md) | **カードリーダー修復ガイド**。WSL2でのUSBデバイス接続 |
| [USB_FIX.md](./USB_FIX.md) | USB接続問題の解決策 |
| [QUICK_FIX_USB.md](./QUICK_FIX_USB.md) | USB問題のクイック修復 |
| [DIAGNOSTICS.md](./DIAGNOSTICS.md) | システム診断ツールの使い方 |

---

### 📊 データ管理・運用

データの取り扱いと日常運用:

| ドキュメント | 説明 |
|------------|------|
| [DATA_VIEWER_EXAMPLES.md](./DATA_VIEWER_EXAMPLES.md) | データビューアーの使用例とExcelエクスポート |
| [SPECIFICATION.md](./SPECIFICATION.md) | システム仕様書・技術仕様 |

---

### 📝 開発・カスタマイズ

開発者向け情報:

| ドキュメント | 説明 |
|------------|------|
| [README_FILES.md](./README_FILES.md) | **ファイル構造ガイド**。プロジェクト内の全ファイル説明 |
| [CHANGELOG.md](./CHANGELOG.md) | 変更履歴・リリースノート |
| [copilot-instructions.md](./copilot-instructions.md) | GitHub Copilot用カスタム指示 |

---

## 🎯 目的別ガイド

### 初めてシステムを使う
1. [QUICKSTART.md](./QUICKSTART.md) - 最速セットアップ
2. [README.md](./README.md) - システム概要理解
3. [MANUAL.md](./MANUAL.md) - 詳細手順

### システムを起動したい
1. [STARTUP_GUIDE.md](./STARTUP_GUIDE.md) - 起動スクリプトの使い方
2. [CARD_READER_FIX.md](./CARD_READER_FIX.md) - カードリーダー問題の解決

### Docker環境を構築したい
1. [DOCKER_UNIT.md](./DOCKER_UNIT.md) - Docker子機構築
2. [NFC_DOCKER_GUIDE.md](./NFC_DOCKER_GUIDE.md) - NFCデバイス設定
3. [MYSQL_MIGRATION.md](./MYSQL_MIGRATION.md) - MySQL環境構築

### 複数のPCで使いたい
1. [MYSQL_MIGRATION.md](./MYSQL_MIGRATION.md) - MySQL移行手順
2. [REMOTE_ACCESS.md](./REMOTE_ACCESS.md) - リモートアクセス設定
3. [IMPLEMENTATION.md](./IMPLEMENTATION.md) - システムアーキテクチャ理解

### トラブルが起きた
1. [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - 総合トラブルシューティング
2. [CARD_READER_FIX.md](./CARD_READER_FIX.md) - カードリーダー問題
3. [USB_FIX.md](./USB_FIX.md) - USB接続問題
4. [DIAGNOSTICS.md](./DIAGNOSTICS.md) - システム診断

### データを確認・エクスポートしたい
1. [DATA_VIEWER_EXAMPLES.md](./DATA_VIEWER_EXAMPLES.md) - データビューアー使用例
2. [SPECIFICATION.md](./SPECIFICATION.md) - データベース仕様

### 開発・カスタマイズしたい
1. [README_FILES.md](./README_FILES.md) - ファイル構造
2. [IMPLEMENTATION.md](./IMPLEMENTATION.md) - 実装詳細
3. [SPECIFICATION.md](./SPECIFICATION.md) - 技術仕様
4. [CHANGELOG.md](./CHANGELOG.md) - 変更履歴

---

## 🆘 よくある質問

**Q: カードリーダーが認識されません**
→ [CARD_READER_FIX.md](./CARD_READER_FIX.md) を参照

**Q: Docker環境でNFCが動作しません**
→ [NFC_DOCKER_GUIDE.md](./NFC_DOCKER_GUIDE.md) を参照

**Q: 複数のPCで同じデータベースを使いたい**
→ [MYSQL_MIGRATION.md](./MYSQL_MIGRATION.md) を参照

**Q: システムが起動しません**
→ [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) → [DIAGNOSTICS.md](./DIAGNOSTICS.md)

**Q: データをExcelでエクスポートしたい**
→ [DATA_VIEWER_EXAMPLES.md](./DATA_VIEWER_EXAMPLES.md) を参照

---

## 🔄 最近の更新

最新の変更内容は [CHANGELOG.md](./CHANGELOG.md) をご覧ください。

### 主要機能

- ✅ **自動カードリーダーアタッチ** - WSL環境で自動的にUSBデバイスをアタッチ
- ✅ **MySQL対応** - 複数デバイスでデータベース共有
- ✅ **Docker完全対応** - 環境構築を簡素化
- ✅ **システム診断機能** - BIOS風の起動時診断
- ✅ **データエクスポート** - Excel形式でデータ取得

---

**📖 Happy Reading! 楽しいOITELUライフを！**
