# 🚀 OITERU かんたんスタートガイド

<div align="center">

**親機・従親機・子機の立ち上げ方法をステップバイステップで説明！**

💻 **プライバシー配慮型ナプキン配布システム**

📅 最終更新: 2026年1月23日

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
| [🔄 リモート設定同期](#-リモート設定同期) | 親機から子機への設定変更 |
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

## 📁 プロジェクトフォルダの場所について

### ⚠️ 重要な注意事項

取説書のコマンド例では `~/oiteru_250827_restAPI` を使っていますが、**実際のパスは環境によって異なります**。

**まず、現在のプロジェクトフォルダのパスを確認してください！**

```bash
# プロジェクトフォルダを探す
find ~ -name "unit.py" 2>/dev/null | grep oiteru
```

**よくあるパスの例：**

| 環境 | パス |
|:---|:---|
| 通常 | `~/oiteru_250827_restAPI` |
| Desktop | `~/Desktop/oiteru_250827_restAPI-1` |
| Documentsフォルダ | `~/Documents/oiteru_250827_restAPI` |

**確認したら、以下の手順で取説書のコマンドを読み替えてください：**

```bash
# 取説書の例
cd ~/oiteru_250827_restAPI

# あなたの環境が ~/Desktop/oiteru_250827_restAPI-1 の場合
cd ~/Desktop/oiteru_250827_restAPI-1
```

> 💡 **ヒント：** `cd` でフォルダに移動できたら、`pwd` で正しいパスを確認できます

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

> ⚠️ **重要: Raspberry Pi OS Bookworm (2023年10月〜) 以降のバージョンについて**
> 
> Raspberry Pi OS BookwormではPEP 668が適用され、システムのPython環境に直接パッケージをインストールすることができなくなりました。
> **仮想環境（venv）の使用が必須**です。
> 
> ```bash
> # ❌ これはエラーになります
> pip install requests
> # error: externally-managed-environment
> 
> # ✅ 仮想環境内で実行してください
> source .venv/bin/activate
> pip install requests
> ```
> 
> 詳細な環境セットアップは `scripts/SETUP_UNIT.md` を参照してください。

#### 📝 手順

1. **必要なパッケージをインストール（Bookworm以降では必須）**
   ```bash
   # python3-fullとpython3-venvをインストール
   sudo apt update
   sudo apt install -y python3-full python3-venv python3-pip
   ```

2. **プロジェクトフォルダに移動**
   ```bash
   cd /home/pi/oiteru_250827_restAPI
   ```

3. **仮想環境をセットアップ（初回のみ）**
   ```bash
   # 仮想環境を作成
   python3 -m venv .venv
   
   # 依存パッケージをインストール
   .venv/bin/pip install -r docker/requirements-client.txt
   
   # システム監視ライブラリをインストール（CPU/メモリ使用率の取得用）
   .venv/bin/pip install psutil
   ```
   
   > 💡 **ヒント**: セットアップを自動化するスクリプトも用意しています：
   > ```bash
   > sudo ./scripts/setup_unit_environment.sh
   > ```

4. **実行権限を付与（初回のみ）**
   ```bash
   chmod +x venv-start.sh
   ```

5. **仮想環境スクリプトを実行（CUIモードがデフォルト）**
   ```bash
   ./venv-start.sh unit
   ```

#### ✨ 初回セットアップが完了したら

2回目以降は以下のコマンドだけでOK：

```bash
cd /home/pi/oiteru_250827_restAPI
./venv-start.sh unit
```

> 💡 **GUIモードで起動したい場合：** `./venv-start.sh unit --gui`

#### ⏸️ 一時退出方法（バックグラウンド実行）

起動中のプログラムを停止せず、SSHセッションから一時的に抜けたい場合：

```bash
# Ctrl + Z を押してプログラムを一時停止
# その後、バックグラウンドに移動
bg

# 確認
jobs
```

**戻りたいとき：**
```bash
# フォアグラウンドに戻す
fg
```

> ⚠️ **注意：** この方法では、SSHを切断するとプログラムが終了します。SSH切断後も動かし続けたい場合は、後述の「遠隔起動・SSH切断後も動作させる方法」を使用してください。

#### 🛑 停止方法

`Ctrl + C` を押す

---

### 💡 遠隔起動・SSH切断後も動作させる方法

**よくある問題：** PowerShellやSSHクライアントを閉じると、子機も一緒に止まってしまう 😱

**原因：** プロセスがSSHセッションに紐づいているため

**解決策は3つ！** 用途別に選んでね 👇

---

####🚀 方法A: `nohup` で起動（一番お手軽！）

**とりあえず動かしたい** ならこれ。SSH切っても動き続けます。

```bash
# パスは自分の環境に合わせて変更してください
cd ~/oiteru_250827_restAPI
# または
cd ~/Desktop/oiteru_250827_restAPI-1

# 仮想環境をセットアップ（初回のみ）
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# Raspberry Pi用ハードウェアライブラリをインストール
.venv/bin/pip install RPi.GPIO Adafruit-PCA9685 pyserial

# 実行権限を確認・付与（初回のみ）
chmod +x venv-start.sh

# バックグラウンドで起動（CUIモードがデフォルト）
nohup ./venv-start.sh unit > unit.log 2>&1 &
```

> 💡 **パスについて：** 上記のセクション「プロジェクトフォルダの場所について」で確認したパスを使用してください  
> 💡 初回のみ仮想環境のセットアップが必要です（2回目以降は不要）  
> 💡 CUIモードがデフォルトです（SSH経由でも安全に起動可能）

**確認：**
```bash
ps aux | grep unit.py
```

**ログを見る：**
```bash
tail -f unit.log
```

**停止するとき：**
```bash
# プロセスIDを確認
ps aux | grep unit.py
# 停止（PIDは上記コマンドで確認した数字）
sudo kill <PID>
```

> ✅ **メリット**
> - コマンド1行で完結
> - SSH切っても動く
> 
> ⚠️ **注意**
> - ラズパイを再起動したら止まる

---

#### 🖥️ 方法B: `tmux` で起動（作業継続したい人向け）

**SSH切っても画面ごと残したい** 場合に便利。あとで再接続してログを確認できます。

**1️⃣ tmuxをインストール（初回のみ）**
```bash
sudo apt install tmux -y
```

**2️⃣ tmuxセッションを開始**
```bash
tmux new -s oiteru
```

**3️⃣ プロジェクトフォルダに移動**
```bash
# パスは自分の環境に合わせて変更してください
cd ~/oiteru_250827_restAPI
# または
cd ~/Desktop/oiteru_250827_restAPI-1
```

**4️⃣ 必要なパッケージをインストール（Bookworm以降では必須）**
```bash
# python3-fullとpython3-venvをインストール
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip
```

> ⚠️ **Raspberry Pi OS Bookworm (2023年10月〜) 以降の注意**
> 
> PEP 668により、仮想環境の使用が必須です。以下のエラーが出る場合は上記コマンドを実行してください：
> ```
> error: externally-managed-environment
> ```

**5️⃣ 仮想環境をセットアップ（初回のみ）**
```bash
# 仮想環境を作成
python3 -m venv .venv

# 依存パッケージをインストール
.venv/bin/pip install -r docker/requirements-client.txt

# システム監視ライブラリをインストール（CPU/メモリ使用率の取得用）
.venv/bin/pip install psutil
```

> 💡 **ヒント**: 自動セットアップスクリプトも用意しています：
> ```bash
> sudo ./scripts/setup_unit_environment.sh
> ```

**6️⃣ 実行権限を確認・付与（初回のみ）**
```bash
# 実行権限を付与
chmod +x venv-start.sh
```

**7️⃣ 子機を起動（CUIモード）**
```bash
./venv-start.sh unit
```

> 🔄 **設定同期について**
> - 親機・従親機からの設定変更が自動的に反映されます
> - Heartbeat経由: 30秒ごとに設定を同期
> - 即時反映: Flask API (ポート5001) で親機から直接受信

**8️⃣ 一時退出（デタッチ）してSSH/PowerShellを閉じてOK！**

```bash
# tmuxセッションから離れる（デタッチ）
Ctrl + B を押してから D を押す
```

> 💡 **ヒント：** デタッチすると、プログラムは動き続けたまま、あなたは通常のターミナルに戻ります。SSH切断してもOK！

**戻りたいとき：**
```bash
tmux attach -t oiteru
```

**セッション一覧：**
```bash
tmux ls
```

**停止するとき：**
```bash
# tmuxセッションに入る
tmux attach -t oiteru
# Ctrl + C で停止
# セッションを終了
exit
```

> ✅ **メリット**
> - ログをリアルタイムで確認できる
> - SSH切ってもセッション継続
> - 複数の作業を並行できる
> 
> ⚠️ **注意**
> - ラズパイを再起動したら止まる

---

#### ⚙️ 方法C: systemdサービス化（最強・本番運用向け）

**常駐アプリ・サーバ・IoT用途なら絶対これ！** ラズパイ起動時に自動で立ち上がります。

**1️⃣ サービスファイルを作成**

```bash
sudo nano /etc/systemd/system/oiteru-unit.service
```

**以下を貼り付け：**

```ini
[Unit]
Description=OITERU Unit Client
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/oiteru_250827_restAPI
ExecStart=/bin/bash /home/pi/oiteru_250827_restAPI/venv-start.sh unit
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/oiteru_250827_restAPI/unit.log
StandardError=append:/home/pi/oiteru_250827_restAPI/unit_error.log

[Install]
WantedBy=multi-user.target
```

> ⚠️ **重要：** systemdサービスファイルでは `~` が使えないため、実際のパスに置き換えてください。  
> 例: `User=hirameki-2` の場合  
> - `WorkingDirectory=/home/hirameki-2/oiteru_250827_restAPI`  
> - `ExecStart=/bin/bash /home/hirameki-2/oiteru_250827_restAPI/venv-start.sh unit`

**保存:** `Ctrl + O` → `Enter` → `Ctrl + X`

**2️⃣ サービスを有効化・起動**

```bash
# 設定を読み込み
sudo systemctl daemon-reload

# 自動起動を有効化
sudo systemctl enable oiteru-unit

# サービスを起動
sudo systemctl start oiteru-unit
```

**3️⃣ 状態確認**

```bash
# 動作状態を確認
sudo systemctl status oiteru-unit

# ログをリアルタイム表示
sudo journalctl -u oiteru-unit -f

# ログファイルを確認
tail -f ~/oiteru_250827_restAPI/unit.log
```

**停止するとき：**

```bash
# 一時停止
sudo systemctl stop oiteru-unit

# 自動起動を無効化
sudo systemctl disable oiteru-unit
```

**再起動：**

```bash
sudo systemctl restart oiteru-unit
```

> ✅ **メリット**
> - SSH不要で動く
> - ラズパイ再起動しても自動で立ち上がる
> - エラーで止まっても自動再起動
> - 本番運用レベル
> 
> ⚠️ **注意**
> - 初期設定が少し手間（でも一度だけ）

---

#### 📊 おすすめ早見表

| 目的 | 方法 | SSH切断後 | 再起動後 | 難易度 |
|:---|:---|:---:|:---:|:---|
| 🧪 **一時的な実験** | `nohup` | ✅ | ❌ | ⭐ |
| 🔍 **開発・デバッグ** | `tmux` | ✅ | ❌ | ⭐⭐ |
| 🏢 **本番運用・常駐** | `systemd` | ✅ | ✅ | ⭐⭐⭐ |

**おすすめ：**
- **ちょっと試したい** → `nohup`
- **開発中・ログ確認したい** → `tmux`
- **研究室や本番で使う** → **`systemd`** 🔥

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

# 🔄 リモート設定同期

親機・従親機の管理画面から、子機の設定をリモートで変更できます！

### ✨ 特長

- 🚀 **即時反映**: 設定変更が数秒で子機に届く
- 🔄 **自動同期**: Heartbeat経由でも30秒ごとに同期
- 📡 **2重の通信経路**: 直接送信 + Heartbeat経由のフォールバック

### 🎯 設定できる項目

| カテゴリ | 設定項目 |
|:---|:---|
| 🔧 **モーター** | タイプ、制御方法、速度、動作時間、回転方向 |
| 📡 **センサー** | 使用有無、GPIOピン、タイムアウト、前後チェック |
| 🌐 **通信** | Heartbeat間隔、Arduinoポート、PCA9685チャンネル |
| 🛠️ **詰まり対策** | 詰まり解除試行回数 |

### 📝 使い方

1. 管理画面にログイン (`http://100.114.99.67:5000/admin`)
2. 「子機管理」→ 対象の子機を選択
3. 「子機設定（リモート設定）」セクションで設定を変更
4. 「📤 設定を子機に送信」ボタンをクリック

### 🔍 動作の仕組み

```
親機管理画面
    │
    ├─【即時送信】──→ 子機Flask API (ポート5001)
    │                  └─ 成功: 即座に反映 ✅
    │
    └─【フォールバック】→ Heartbeat待ち
                          └─ 次回接続時に反映 🔄
```

### 💡 ヒント

- ✅ 子機がオンラインなら **即座に反映**
- ⏰ 子機がオフラインでも **次回接続時に自動反映**
- 🔄 親機の画面も **設定送信後に即座に更新される**

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

## � pip installで「externally-managed-environment」エラー

**Raspberry Pi OS Bookworm（2023年10月〜）以降** でこのエラーが出ます：

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install python3-xyz
```

### 原因

PEP 668により、システムのPython環境を保護するため、直接パッケージをインストールすることができなくなりました。

### ✅ 解決方法: 仮想環境を使う（推奨）

```bash
# 必要なパッケージをインストール
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip

# プロジェクトフォルダに移動
cd /home/pi/oiteru_250827_restAPI

# 仮想環境を作成
python3 -m venv .venv

# 仮想環境をアクティベート
source .venv/bin/activate

# これでpip installが使えるようになります
pip install requests flask psutil
```

> 💡 **ヒント**: 自動セットアップスクリプトも用意しています：
> ```bash
> sudo ./scripts/setup_unit_environment.sh
> ```

### ❌ 非推奨の方法

以下の方法は **システムを壊す可能性があるため非推奨** です：

```bash
# ❌ これは使わないでください
pip install --break-system-packages requests
```

---

## �🔌 接続できない

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

## �️ tmuxで「duplicate session」エラーが出る

```bash
duplicate session: oiteru
```

このエラーは、既に同じ名前のセッションが存在している場合に発生します。

### 解決方法1: 既存のセッションに接続（おすすめ）

```bash
tmux attach -t oiteru
```

### 解決方法2: セッションをリセット

```bash
# 既存のセッションを削除
tmux kill-session -t oiteru

# 新規作成
tmux new -s oiteru
```

### 確認: セッション一覧を見る

```bash
tmux ls
```

---

## 🖼️ SSH経由で「no display name」エラーが出る

```bash
_tkinter.TclError: no display name and no $DISPLAY environment variable
```

このエラーは、SSH経由で起動した際にX11ディスプレイがない場合に発生します。

### 解決方法1: CUIモードで起動（おすすめ・デフォルト）

```bash
# 通常起動（CUIモードがデフォルト）
./venv-start.sh unit
```

nohupやtmuxで使う場合：

```bash
# nohupの場合
nohup ./venv-start.sh unit > unit.log 2>&1 &

# tmux内で起動する場合
./venv-start.sh unit
```

### 解決方法2: X11転送を使う

SSH接続時に `-X` オプションを付けてX11転送を有効にします：

```bash
# X11転送を有効にしてSSH接続
ssh -X pi@100.xxx.xxx.xxx

# 通常通り起動
cd ~/oiteru_250827_restAPI
./venv-start.sh unit
```

> 💡 **ヒント：** 本番運用では、systemdサービス化（方法C）を使うとこの問題は発生しません
」エラーが出る

```bash
ModuleNotFoundError: No module named 'requests'
ModuleNotFoundError: No module named 'RPi'
```

このエラーは、必要なPythonパッケージがインストールされていない場合に発生します。

### 解決方法: 不足しているパッケージをインストール

```bash
# すべての依存パッケージを再インストール
.venv/bin/pip install -r requirements.txt

# Raspberry Pi用ハードウェアライブラリをインストール
.venv/bin/pip install RPi.GPIO Adafruit-PCA9685 pyserial

# 起動
./venv-start.sh unit
```

### 特定のパッケージだけインストールする場合

```bash
# requestsをインストール
.venv/bin/pip install requests

# RPi.GPIOをインストール
.venv/bin/pip install RPi.GPIO Adafruit-PCA9685 pyseriall -r requirements.txt

# 起動
./venv-start.sh unit
```

---
## �🐳 MySQLに接続できない

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

📅 最終更新: 2026年1月23日

</div>



🚀 親機起動
親機（MySQL版）が正常に起動し、http://localhost:5000 で稼働中です。

📝 venv-start スクリプト対応
Windows (venv-start.ps1)

.\venv-start.ps1 parent-sqlite   # 親機 (SQLite版).\venv-start.ps1 parent-mysql    # 親機 (MySQL版).\venv-start.ps1 sub-parent      # 従親機 (MySQL版).\venv-start.ps1 unit            # 子機 (引数渡し対応).\venv-start.ps1 unit --gui      # 子機 GUIモード
Linux/Mac (venv-start.sh)

./venv-start.sh parent-sqlite    # 親機 (SQLite版)./venv-start.sh parent-mysql     # 親機 (MySQL版)./venv-start.sh sub-parent       # 従親機 (MySQL版)./venv-start.sh unit             # 子機 (引数渡し対応)./venv-start.sh unit --gui       # 子機 GUIモード
📦 ライブラリー依存関係の整備
1. 親機・従親機用
requirements.txt + requests>=2.32.0
requirements.mysql.txt + requests>=2.28.0
2. 子機用
requirements-client.txt + flask>=3.0.0
🔄 設定同期の案内表示
GUIモード
ウィンドウ上部に「🔄 親機・従親機からの設定変更が自動的に反映されます」と表示
CUIモード
起動時に以下を表示:


🔄 親機・従親機からの設定変更が自動的に反映されます   - Heartbeat経由: 30秒ごとに設定を同期   - 即時反映: Flask API (ポート5001) で受信
🎯 動作確認済み
✅ 親機が起動中（MySQL版） ✅ venv-start.ps1/sh で全モード対応 ✅ 子機起動時に設定同期の案内を表示 ✅ 全ての依存ライブラリーを適切に配置 ✅ GitHubに同期完了

これで、親機・従親機・子機の3方向すべてで設定同期が可能になり、起動スクリプトも統一されました！🎉