# 🚀 OITERU かんたんスタートガイド

<div align="center">

**親機・従親機・子機の立ち上げ方法をステップバイステップで説明！**

💻 **プライバシー配慮型ナプキン配布システム**

📅 最終更新: 2026年1月16日

> 💡 **スマホで見る場合は [QUICKSTART.html](QUICKSTART.html) がおすすめです！**

</div>

---

## 📋 目次

| セクション | 内容 |
|:---|:---|
| [🎯 はじめに](#-はじめに) | OITERUとは？用語の説明 |
| [🖥️ 親機の起動方法](#%EF%B8%8F-親機の起動方法) | メインサーバーの起動 |
| [🔗 従親機の起動方法](#-従親機の起動方法) | サブサーバーの起動 |
| [📡 子機の起動方法](#-子機の起動方法) | ラズパイ端末の起動 |
| [⚙️ 管理画面の使い方](#%EF%B8%8F-管理画面の使い方) | Web管理画面 |
| [🔧 トラブルシューティング](#-トラブルシューティング) | 困ったときは |

---

## 🎯 はじめに

### OITERUって何？

ICカードをかざすと、**生理用ナプキンが自動で提供される**プライバシー配慮型の配布システムです！

### 💡 システムの特長

- 🔒 **プライバシー保護**: 誰にも見られずに受け取れる
- 📱 **簡単操作**: ICカードをかざすだけ
- 📊 **在庫管理**: 個人ごとの配布数を自動管理
- 🌐 **複数拠点対応**: 学校や職場の複数箇所に設置可能

```
   ┌─────────────┐                ┌────────────┐
   │   ICカード   │  ───ピッ───▶  │   子機     │  ───▶  🩹 ナプキン！
   │  (社員証等)  │                │ (ラズパイ) │
   └─────────────┘                └─────┬──────┘
                                        │
                                        ▼ 通信
                                  ┌────────────┐
                                  │   親機     │  📊 利用履歴を管理
                                  │ (サーバー) │  🔒 プライバシー保護
                                  └────────────┘
```

### 用語の説明

| 用語 | 説明 | IPアドレス |
|:---:|:---|:---:|
| 🖥️ **親機** | データベースを持つメインサーバー | `100.114.99.67` |
| 🔗 **従親機** | 親機のDBを参照するサブサーバー | 設置場所による |
| 📡 **子機** | ナプキンを排出するラズパイ端末 | 設置場所による |

> 💡 **Tailscale**を使っているので、親機のアドレスは `100.114.99.67` で固定です！

---

# 🖥️ 親機の起動方法

親機はデータベース（MySQL）を持つメインサーバーです。

---

### 方法1: 🚀 ランチャーで起動（一番簡単！）

1. `scripts` フォルダを開く
2. `launcher.bat` をダブルクリック
3. **「1. GUI版」** を選択
4. 画面で：
   - 起動モード: **「親機」** を選択
   - 実行方法: **「Dockerモード」** を選択
   - **「起動」** ボタンを押す

> ✅ **これだけ！** 🎉

---

### 方法2: 🐳 Dockerで起動（推奨）

```powershell
cd C:\Users\RTDS_admin\source\repos\CYLIU2003\oiteru_250827_restAPI
docker-compose -f docker-compose.mysql.yml up -d
```

**確認：**
```powershell
docker ps
```
→ `oiteru_mysql` と `oiteru_web` が `Up` になっていればOK！

**停止するとき：**
```powershell
docker-compose -f docker-compose.mysql.yml down
```

---

### 方法3: 🐍 仮想環境で起動（開発向け）

```powershell
cd C:\Users\RTDS_admin\source\repos\CYLIU2003\oiteru_250827_restAPI
.\venv-start.ps1 parent-mysql
```

> ⚠️ MySQLが別途起動している必要があります

---

### 方法4: 🔧 通常モードで起動（非推奨・テスト用）

仮想環境を使わず直接実行します。環境が汚れるので非推奨。

```powershell
# 環境変数を設定
$env:DB_TYPE = 'mysql'
$env:MYSQL_HOST = 'localhost'
$env:MYSQL_PORT = '3306'
$env:MYSQL_DATABASE = 'oiteru'
$env:MYSQL_USER = 'oiteru_user'
$env:MYSQL_PASSWORD = 'oiteru_password_2025'

# 起動
python server.py
```

---

# 🔗 従親機の起動方法

従親機は、親機のデータベースを参照するサブサーバーです。複数拠点で運用するときに使います。

---

### ステップ0: 前準備 - config.json を設定

#### 🚀 方法A: ウィザードで設定（おすすめ！）

```powershell
# Windows
.\scripts\setup_config.ps1

# Linux
./scripts/setup_config.sh
```

> 画面の質問に答えるだけで設定完了！

#### ⚡ 方法B: ワンライナーで設定

```bash
# 例: 従親機Bを設定
./scripts/setup_config.sh sub-parent "従親機B" "別館2階"
```

#### 📝 方法C: テンプレートをコピー

```bash
cp config_templates/config_sub_parent.template.json config.json
nano config.json  # ★マークの項目を編集
```

---

### 方法1: 🚀 ランチャーで起動

1. `scripts/launcher.bat` をダブルクリック
2. GUI版を選択
3. 起動モード: **「従親機」** を選択
4. 設定で **MySQLホスト** を `100.114.99.67` に変更
5. 「起動」ボタンを押す

---

### 方法2: 🐳 Dockerで起動

```bash
./docker-start.sh external
```

または：

```bash
cd docker
docker-compose -f docker-compose.external-db.yml up -d
```

---

### 方法3: 🐍 仮想環境で起動

**Windows (PowerShell)：**

```powershell
# 親機のMySQLに接続する場合
$env:MYSQL_HOST = '100.114.99.67'
.\venv-start.ps1 sub-parent
```

**Linux / Mac：**

```bash
export MYSQL_HOST=100.114.99.67
./venv-start.sh sub-parent
```

---

### 方法4: 🔧 通常モードで起動（非推奨）

```powershell
$env:DB_TYPE = 'mysql'
$env:MYSQL_HOST = '100.114.99.67'
$env:MYSQL_PORT = '3306'
$env:MYSQL_DATABASE = 'oiteru'
$env:MYSQL_USER = 'oiteru_user'
$env:MYSQL_PASSWORD = 'oiteru_password_2025'
$env:SERVER_NAME = '従親機A'

python server.py
```

---

# 📡 子機の起動方法

子機はRaspberry Piで動き、NFCカードの読み取りとナプキンの排出を行います。

---

### ステップ0: 前準備 - config.json を設定

#### 🚀 方法A: ウィザードで設定（おすすめ！）

対話形式で簡単に設定できます：

```bash
cd /home/pi/oiteru_250827_restAPI/scripts
./setup_config.sh
```

> 画面の質問に答えるだけで設定完了！

#### ⚡ 方法B: ワンライナーで設定（上級者向け）

```bash
# 例: 3号機を設定
./scripts/setup_config.sh unit "3号機" "7号館1階" "password123"
```

#### 📝 方法C: テンプレートをコピー

```bash
# テンプレートをコピー
cp config_templates/config_unit.template.json config.json

# ★マークの項目を編集
nano config.json
```

#### 🔧 方法D: 手動で編集

```bash
nano /home/pi/oiteru_250827_restAPI/config.json
```

**以下の3箇所を変更：**

```json
{
    "SERVER_URL": "http://100.114.99.67:5000",
    "UNIT_NAME": "あなたの子機名",
    "UNIT_PASSWORD": "あなたのパスワード"
}
```

| 設定 | 何を入れる？ | 例 |
|:---|:---|:---|
| `SERVER_URL` | 親機のアドレス（固定） | `http://100.114.99.67:5000` |
| `UNIT_NAME` | 子機の名前（管理画面で登録したもの） | `1号機` |
| `UNIT_PASSWORD` | パスワード（管理画面で設定したもの） | `password123` |

> ⚠️ **注意**
> - `http://` で始まる（`https://` じゃない！）
> - 最後にスラッシュ `/` は付けない

**保存:** `Ctrl + O` → `Enter` → `Ctrl + X`

---

### 方法1: ⚡ クイック起動スクリプト（おすすめ！）

```bash
cd /home/pi/oiteru_250827_restAPI/scripts
sudo ./quick_start_unit.sh 100.114.99.67
```

> 親機のIPアドレスを引数に渡すだけ！

---

### 方法2: 🐍 仮想環境で起動（開発・デバッグ向け）

#### 📝 手順

1. **プロジェクトフォルダに移動**
   ```bash
   cd /home/pi/oiteru_250827_restAPI
   ```

2. **仮想環境スクリプトを実行**
   ```bash
   ./venv-start.sh unit
   ```

#### ✨ スクリプトが自動でやってくれること

- `.venv` フォルダがなければ、自動作成
- 必要なPythonパッケージを自動インストール
- 仮想環境を起動して、`unit.py` を実行

#### 💡 実行権限がない場合

もしエラーが出た場合は、以下で実行権限を付与してください：

```bash
chmod +x venv-start.sh
```

#### 🛑 停止方法

`Ctrl + C` を押す

---

### 方法3: 🔧 通常モードで起動（非推奨）

仮想環境を使わず、システムのPython環境で直接実行する方法です。

```bash
cd /home/pi/oiteru_250827_restAPI
sudo python3 unit.py
```

> ⚠️ **注意:** この方法は依存関係の管理が難しいため、できる限り **方法1** か **方法2** を使ってください。

---

### 方法4: 🔄 自動起動の設定

電源ON時に自動で子機を起動させたい場合：

```bash
# サービス登録
sudo cp /home/pi/oiteru_250827_restAPI/oiteru-unit.service /etc/systemd/system/
sudo systemctl enable oiteru-unit
sudo systemctl start oiteru-unit

# 確認
sudo systemctl status oiteru-unit
```

---

# ⚙️ 管理画面の使い方

ブラウザで以下にアクセス：

```
🌐 http://100.114.99.67:5000/admin
🔑 初期パスワード: admin
```

### できること

| メニュー | 説明 |
|:---|:---|
| 👥 ユーザー管理 | ユーザーの登録・編集、個人在庫数調整 |
| 🤖 子機管理 | 子機の登録・接続状態確認・在庫管理 |
| 📜 利用履歴 | 匿名化された利用統計の確認 |
| ⚙️ 設定 | 自動登録モード、1日の配布上限数など |
| 🔒 プライバシー | 個人情報保護とデータ管理設定 |

> 💡 **プライバシーに配慮した設計**
> 利用履歴は統計目的で記録されますが、個人を特定する情報は含まれません。

---

# 🔧 トラブルシューティング

---

## 🔒 PowerShellでスクリプトが実行できない

こんなエラーが出た場合：
```
このシステムではスクリプトの実行が無効になっているため...
```

### 解決方法1: バッチファイルを使う（おすすめ）

`.ps1` の代わりに `.bat` ファイルを使ってください：

```
.\scripts\setup_config.ps1  ← ❌ エラーになる
.\scripts\setup_config.bat  ← ✅ OK！
```

### 解決方法2: 実行ポリシーを変更する

```batch
scripts\fix_powershell_policy.bat
```

このバッチファイルを実行すると、PowerShellスクリプトが使えるようになります。

### 解決方法3: コマンドで一時的に許可

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_config.ps1
```

---

## 🔌 接続できない

### 1. Tailscaleは接続してる？

```bash
tailscale status
```

「connected」と出てなければ：

```bash
sudo tailscale up
```

### 2. サーバーは起動してる？

ブラウザで `http://100.114.99.67:5000` を開いてみる

### 3. config.json は正しい？

- `http://` で始まる？（`https://` じゃない）
- 最後にスラッシュ `/` は付いてない？
- ポート番号 `:5000` は付いてる？

---

## 📱 NFCカードが読めない

### 1. USBが抜けてない？

NFCリーダーのUSBケーブルを確認

### 2. デバイスが認識されてる？

```bash
lsusb
```

→ Sony か ACS のデバイスが表示されればOK

### 3. ラズパイを再起動

```bash
sudo reboot
```

---

## 🩹 ナプキンが出ない

- 在庫は残ってる？（管理画面で確認）
- 1日の上限に達してない？
- モーターの配線は正しい？
- 排出口が詰まってない？

---

## 🐳 MySQLに接続できない

### Dockerが起動してる？

```powershell
docker ps
```

→ `oiteru_mysql` が表示されてなければ：

```powershell
docker-compose -f docker-compose.mysql.yml up -d
```

---

# 📋 起動方法まとめ

| 対象 | おすすめ | コマンド |
|:---:|:---|:---|
| 🖥️ 親機 | 🐳 Docker | `docker-compose -f docker-compose.mysql.yml up -d` |
| 🖥️ 親機 | 🐍 仮想環境 | `.\venv-start.ps1 parent-mysql` |
| 🔗 従親機 | 🐍 仮想環境 | `.\venv-start.ps1 sub-parent` |
| 📡 子機 | ⚡ クイック起動 | `sudo ./quick_start_unit.sh 100.114.99.67` |
| 📡 子機 | 🐍 仮想環境 | `./venv-start.sh unit` |

---

# 🛠️ スクリプト一覧

| スクリプト | 場所 | 説明 |
|:---|:---|:---|
| 🚀 `launcher.bat` | scripts/ | ランチャー（Windows） |
| 🚀 `launcher.sh` | scripts/ | ランチャー（Linux） |
| ⚡ `quick_start_unit.sh` | scripts/ | 子機クイック起動 |
| 🐍 `venv-start.ps1` | / | 仮想環境起動（Windows） |
| 🐍 `venv-start.sh` | / | 仮想環境起動（Linux） |
| 🐳 `docker-start.sh` | / | Docker起動 |

---

# 📞 困ったら

管理者に連絡！その時、以下を伝えてね：

| 項目 | 例 |
|:---|:---|
| 1️⃣ **何をしたか** | 「カードをかざした」 |
| 2️⃣ **何が起きたか** | 「エラーが出た」 |
| 3️⃣ **エラーメッセージ** | 画面に出た文字 |
| 4️⃣ **子機の名前** | `UNIT_NAME` の値 |

---

<div align="center">

**わからないことがあったら、遠慮なく管理者にお問い合わせください！** 😊

📅 最終更新: 2026年1月16日

</div>
