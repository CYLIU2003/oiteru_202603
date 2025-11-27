# OITELU 親機 起動スクリプト

## 📋 概要

親機（REST APIサーバー）を起動する際に、自動的にカードリーダーの検出・接続を行うスクリプトです。

## 🚀 起動方法

### WSL環境（推奨）

#### MySQL版（推奨）
```bash
./start_oiteru_mysql.sh
```

または、Windowsから:
```
start_oiteru_mysql.bat をダブルクリック
```

#### SQLite版
```bash
./start_oiteru.sh
```

---

## 🔧 自動処理の内容

起動スクリプトは以下の処理を自動的に実行します:

### 1. カードリーダー自動アタッチ ✨

- **WSL環境の自動検出**: `/proc/version` を確認してWSL環境かどうかを判定
- **カードリーダーの確認**: `lsusb` でカードリーダーが既に認識されているかチェック
- **Windows側からの自動アタッチ**: 
  - カードリーダーが見つからない場合、Windows側の `usbipd` を使って自動的にアタッチ
  - BUSID を自動検出（054c:06c1 = Sony RC-S380/S）
  - 既存の接続を解除してから再アタッチ
  - `--auto-attach` オプションで再起動後も自動接続

### 2. Docker確認

- Docker がインストールされているか確認
- Docker デーモンが起動しているか確認

### 3. Dockerコンテナ起動

- **MySQL版**: `docker-compose.mysql.yml` でコンテナ起動
- **SQLite版**: `docker-compose.yml` でコンテナ起動

### 4. カードリーダー初期化

- Docker コンテナ内で `pcscd` (PC/SC Daemon) を起動
- カードリーダーが正常に動作するか確認

### 5. システム診断

- `diagnostics.py` を実行してシステム全体の健全性をチェック

---

## 📁 関連ファイル

### 起動スクリプト
- `start_oiteru_mysql.sh` - MySQL版起動スクリプト（推奨）
- `start_oiteru_mysql.bat` - Windows用ランチャー（MySQL版）
- `start_oiteru.sh` - SQLite版起動スクリプト
- `auto_attach_card_reader.sh` - カードリーダー自動アタッチスクリプト

### カードリーダー手動修復用
- `fix_card_reader.bat` - カードリーダー完全修復（PowerShell）
- `fix_card_reader.ps1` - PowerShellスクリプト本体
- `attach_card_reader.bat` - カードリーダー接続（PowerShell）
- `attach_card_reader.ps1` - PowerShellスクリプト本体

---

## 🔍 動作フロー

```
起動スクリプト実行
    ↓
[1] WSL環境を検出
    ↓
[2] カードリーダーがWSL側にあるか確認
    ├─ あり → 次のステップへ
    └─ なし → Windows側からusbipdで自動アタッチ
              ↓
              BUSID自動検出 (054c:06c1)
              ↓
              usbipd detach (既存接続解除)
              ↓
              usbipd attach --wsl --auto-attach
              ↓
              2秒待機してデバイス認識確認
    ↓
[3] Docker確認・起動
    ↓
[4] コンテナ内でpcscd起動
    ↓
[5] システム診断実行
    ↓
完了！
```

---

## ⚙️ 設定

### 自動検出されるカードリーダー

- **ベンダーID**: 054c (Sony)
- **プロダクトID**: 06c1 (RC-S380/S)
- **検索パターン**: `054c:06c1`, `RC-S380`, `sony`, `rc-s`

別のカードリーダーを使用する場合は、`auto_attach_card_reader.sh` 内の検索パターンを変更してください。

```bash
# 例: 別のカードリーダーの場合
if lsusb 2>/dev/null | grep -qi "YOUR_VENDOR_ID:YOUR_PRODUCT_ID"; then
```

---

## 🐛 トラブルシューティング

### カードリーダーが認識されない場合

#### 自動修復を試す:
```bash
./fix_card_reader.bat  # Windows PowerShell で実行
```

#### 手動で確認:
```bash
# Windows側でカードリーダーを確認
powershell.exe -Command "usbipd list"

# WSL側で確認
lsusb | grep Sony

# カードリーダーのBUSIDを確認して手動アタッチ
powershell.exe -Command "usbipd attach --wsl --busid 1-4"
```

### pcscd が起動しない場合

```bash
# コンテナ内でpcscdを手動起動
docker exec -it oiteru_flask bash
pkill -9 pcscd
pcscd
pcsc_scan  # カードリーダーをテスト
```

### Docker が起動しない場合

```bash
# Dockerサービスを起動
sudo service docker start

# または WSL を再起動
wsl --shutdown
# WSLを再度開く
```

---

## 📖 使用例

### 通常の起動（Windows）

```
1. start_oiteru_mysql.bat をダブルクリック
2. 自動的にカードリーダーがアタッチされます
3. ブラウザで http://localhost:5000 にアクセス
```

### WSLターミナルから起動

```bash
cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI
./start_oiteru_mysql.sh
```

### カードリーダーだけ修復

```
fix_card_reader.bat をダブルクリック
```

---

## 🎯 管理画面

起動完了後、以下のURLにアクセスできます:

- **管理画面**: http://localhost:5000/admin
- **ユーザー画面**: http://localhost:5000
- **MySQL**: localhost:3306 (ユーザー: oiteru_user, パスワード: oiteru_password)

---

## 🛑 停止方法

### MySQL版
```bash
docker-compose -f docker-compose.mysql.yml down
```

### SQLite版
```bash
docker-compose down
```

---

## 📝 ログ確認

```bash
# MySQL版
docker-compose -f docker-compose.mysql.yml logs -f

# SQLite版
docker-compose logs -f

# Flaskコンテナのみ
docker logs -f oiteru_flask

# MySQLコンテナのみ
docker logs -f oiteru_mysql
```

---

## 🔐 セキュリティ

- カードリーダーのアタッチには **管理者権限** が必要です
- Windows側で `usbipd` コマンドを使用するため、UACプロンプトが表示されます
- 自動アタッチスクリプトは安全に設計されていますが、必要に応じて `auto_attach_card_reader.sh` の内容を確認してください

---

## 📚 参考資料

- [CARD_READER_FIX.md](./CARD_READER_FIX.md) - カードリーダートラブルシューティング完全ガイド
- [MYSQL_MIGRATION.md](./取説書/MYSQL_MIGRATION.md) - MySQL移行ガイド
- [NFC_DOCKER_GUIDE.md](./取説書/NFC_DOCKER_GUIDE.md) - Docker環境でのNFC設定
- [QUICKSTART.md](./取説書/QUICKSTART.md) - クイックスタートガイド
