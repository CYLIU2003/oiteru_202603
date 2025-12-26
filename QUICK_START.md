# 🚀 OITERUシステム クイック起動ガイド

## 📌 1分で起動する方法

### 親機（データベース持ち）

**Windows:**
```powershell
.\scripts\quick_start_parent.ps1
```

**Mac/Linux:**
```bash
./scripts/quick_start_parent.sh
```

### 従親機（親機のDBに接続）

**Windows:**
```powershell
.\scripts\quick_start_sub.ps1 -Host 192.168.1.100
```

**Mac/Linux:**
```bash
./scripts/quick_start_sub.sh 192.168.1.100
```

### 子機（Raspberry Pi）

```bash
sudo ./scripts/quick_start_unit.sh 192.168.1.100
```

---

## 🐍 仮想環境モード vs 🐳 Dockerモード

### 仮想環境モード（推奨・初心者向け）
- **特徴:** Python仮想環境 + Docker(MySQL)
- **起動:** `quick_start_parent.ps1`
- **メリット:** 軽量、デバッグしやすい
- **用途:** 開発環境、テスト環境

### Dockerモード（本番運用向け）
- **特徴:** 全てDockerコンテナで実行
- **起動:** `quick_start_parent.ps1 -Docker`
- **メリット:** 環境の完全隔離、本番安定性
- **用途:** 本番サーバー、複数サーバー運用

---

## 📡 アクセスURL

起動後、以下のURLにアクセスできます：

- **トップページ:** http://localhost:5000
- **管理画面:** http://localhost:5000/admin
  - パスワード: `admin`

---

## 📚 詳しい説明

詳細なセットアップ手順は以下を参照してください：

- **クイックスタートガイド:** `取説書/QUICKSTART.md`
- **詳細マニュアル:** `取説書/README.md`

---

## ❓ トラブルシューティング

### 仮想環境が見つからない
→ スクリプトが自動で作成します（初回のみ時間がかかります）

### MySQLコンテナが起動しない
→ Docker Desktopが起動しているか確認してください

### 子機が親機に接続できない
→ 親機のIPアドレスが正しいか確認してください
→ ファイアウォールでポート5000/3306が開いているか確認してください

---

**最終更新: 2025年12月26日**
