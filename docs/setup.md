# 親機・子機の初回セットアップ

<a id="setup"></a>

## 始める前に

この文書は、新しい親機・子機を導入する設置担当者向けです。
日常の当番は [QUICK_START.md](../QUICK_START.md) を使ってください。
すでに稼働中の機械では、`.env` の上書きや秘密鍵の作り直しをしないでください。

### 作業する機械を区別する

| 作業場所 | すること |
| --- | --- |
| 担当者の PC | ブラウザで画面を見る。必要なら SSH で親機・子機へ接続する |
| 親機（Linux） | MySQL 8 と親機サービスを準備する |
| 子機（Raspberry Pi） | リーダー・モーターなどを準備し、親機へ接続する |

SSH は「別の PC のターミナルへ入る」操作です。
`ssh <ユーザー名>@<ホスト名>` の `<...>` は、かっこごと実際の値へ置き換えます。
`https://<親機ホスト名>` も同様です。URL には `https://` を 1 回だけ付けます。

コマンドは、対象の機械にある **`oiteru_202603` フォルダの中**で実行します。
現在の親機での場所は `~/デスクトップ/oiteru_202603` です。
新規設置でホームフォルダに取得した場合は `~/oiteru_202603` になります。

```bash
# 現在の親機へ、SSH 設定済みの担当者 PC から入る例
ssh hirameki-3
cd ~/デスクトップ/oiteru_202603
```

新規の親機・子機にまだファイルがなければ、その機械で Git を準備して取得します。

```bash
sudo apt update
sudo apt install -y git
cd ~
git clone https://github.com/CYLIU2003/oiteru_202603.git
cd oiteru_202603
```

設定する URL・子機名・機器の場所は [引き継ぎ票](handover.md) に残します。

**進める順番：** 親機の準備 → 親機の応答確認 → 子機の準備 → 管理画面で承認 → 子機起動 → テストカードで確認。
標準構成では MySQL 8（InnoDB）を使い、SQLite や旧 Docker 起動手順は使いません。
親機は systemd（OS が起動・再起動を管理する仕組み）、この手順の子機は tmux（接続を切っても動かせる作業画面）を使います。

<a id="setup-parent"></a>

## 1. 親機を準備する

### 1-1. 用意するもの

**実行する場所：親機の Linux ターミナル。通常のログインユーザーで作業します。**

この手順は、`apt` と systemd が使える Ubuntu などの Linux、ローカル MySQL 8 を前提にしています。
担当者と、管理者アカウント・設置場所・公開 URL を決めておいてください。
外部 MySQL の構成は、この手順の対象外です。ここで使う `parent.sh install` は、
ローカルの `mysql.service` を必要とするため、別構成は設置担当者と手順を決めてください。

Python と基本ツールを準備します。

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tmux curl openssl libusb-1.0-0
```

`sudo` は管理者権限で実行するための指定です。聞かれるのは Linux のログインパスワードで、
管理画面のパスワードとは別です。入力しても画面に文字は表示されません。

### 1-2. 親機の秘密設定を作る

初回だけ、設定の見本から `.env` を作ります。

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

`.env` はパスワードや DB 接続先を入れるファイルです。`chmod 600` は所有者だけが読み書きできるようにします。
`nano` では編集後に **Ctrl + O → Enter** で保存し、**Ctrl + X** で閉じます。

| 設定 | 入れるもの |
| --- | --- |
| `SERVER_NAME` / `SERVER_LOCATION` | 親機名と設置場所 |
| `FLASK_SECRET_KEY` | 管理画面のセッション保護用。32 文字以上のランダム値 |
| `OITERU_ADMIN_USERNAME` | 管理画面のユーザー名 |
| `OITERU_ADMIN_PASSWORD` | 管理画面のパスワード。12 文字以上 |
| `CARD_UID_HMAC_KEY` | カード識別子の保護用。32 文字以上の別のランダム値 |
| `DB_TYPE` | `mysql` のまま |
| `MYSQL_HOST` / `MYSQL_PORT` | 親機内の DB なら `localhost` / `3306` |
| `MYSQL_USER` / `MYSQL_PASSWORD` | OITERU 用 DB ユーザー名と、専用の強いパスワード |
| `MYSQL_DATABASE` | 通常は `oiteru` |
| `MYSQL_ROOT_PASSWORD` | このローカル構築スクリプトでは使わない。設定する場合は見本の値を変更する |

`change-this-...` の値は見本です。実際の秘密値に置き換えてください。
ランダム値は、次を必要な項目ごとに実行して作れます。値をチャットや資料へ貼らないでください。

```bash
openssl rand -hex 32
```

運用中の `CARD_UID_HMAC_KEY` は、気軽に変更しないでください。登録済みカードとの照合に影響します。
`FLASK_SECRET_KEY` の変更も管理者セッションを無効にします。

標準のネットワーク運用では、次の値を維持します。

```dotenv
OITERU_STRICT_SECURITY=true
SESSION_COOKIE_SECURE=true
```

**HTTPS は別途設定が必要です。** 設置担当者がリバースプロキシなどで HTTPS の入口を用意し、
ブラウザと子機はその URL へ接続します。HTTPS を準備するまでは学内向けの運用を始めないでください。

親機上の `http://127.0.0.1:5000/` で閉じた検証をする場合だけ、次の 2 項目を `false` にします。
親機サービスは標準で全ネットワークインターフェースの 5000 番ポートを使うため、
検証中はファイアウォールなどで外部からの接続を遮断します。運用に戻す前に両方を `true` に戻して再起動します。

```dotenv
OITERU_STRICT_SECURITY=false
SESSION_COOKIE_SECURE=false
```

### 1-3. Python 環境と MySQL を準備する

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
```

MySQL がすでに導入済みなら、最後は `scripts/setup_local_mysql.sh` として `--install` を外します。
スクリプトは `.env` を読み、ローカル MySQL の起動、DB・ユーザーの作成、接続確認を行います。
使用するのが MySQL 8 であることを `mysql --version` でも確認してください。

**できた目印：** `OITERU local MySQL is ready` と `Local MySQL setup completed.` が表示されます。
末尾に tmux で親機を起動する案内が出ても、標準構成では次の `parent.sh install` へ進みます。

### 1-4. 親機を起動して確認する

```bash
scripts/parent.sh install
```

`sudo` は付けずに実行します。必要なところでパスワードを聞かれます。
親機を `oiteru-parent` サービスとして登録し、PC 再起動時の自動起動も有効にします。
DB の表と migration は、親機起動時に適用されます。手書き SQL を本番へ直接流す必要はありません。

```bash
scripts/parent.sh status
curl --fail http://127.0.0.1:5000/api/health
```

**できた目印：** `status` の最後が「問題ありません。」となり、`curl` の返事に `"status":"ok"` が含まれます。
`/api/health` は親機の応答確認です。DB・リーダー・排出の確認は、この後も必要です。

ブラウザで `https://<親機ホスト名>/admin` を開き、`.env` に設定した管理者アカウントでログインします。
ローカル検証の場合だけ、設定を合わせたうえで `http://127.0.0.1:5000/admin` を使います。
この `127.0.0.1` は「今ブラウザを動かしている PC 自身」を指します。

親機のカード登録も確認する場合は、USB リーダーを接続して次を実行します。

```bash
.venv/bin/python tools/check_nfc_reader.py
```

認識されなければ [親機の復旧手順](runbook.md#障害時の対処表) を参照してください。
Windows の開発環境で使う場合は [専用のリーダー設定手順](card_reader_windows.md) があります。

<a id="setup-unit"></a>

## 2. Raspberry Pi 子機を準備する

### 2-1. 子機へ接続する

**実行する場所：Raspberry Pi のターミナル。親機のターミナルとは別です。**
通常ユーザーでログインし、取得済みのプロジェクトへ移動します。

```bash
ssh <子機ユーザー名>@<子機ホスト名>
cd ~/oiteru_202603
```

保存先が Desktop やデスクトップの場合は、その実際の場所へ読み替えてください。
子機プログラムは Raspberry Pi 上で root 実行を拒否します。起動に `sudo` を付けないでください。

### 2-2. 必要なソフトウェアを準備する

```bash
scripts/setup_unit_environment.sh
```

Python 環境、子機用パッケージ、NFC・I2C・tmux などを準備します。
**OS のパッケージ更新も行うため、新規設置や保守の時間に実行します。**
I2C（機器との通信方式）を新しく有効にした場合は、案内に従って再起動します。

```bash
sudo reboot
```

再起動すると SSH 接続は切れます。起動を待ち、もう一度接続してプロジェクトへ移動してください。

### 2-3. 子機の設定を確認する

```bash
nano config.json
```

`config.json` は子機名や配線などの設定です。値は実機に合わせ、設置担当者と確認します。
JSON では、文字列を `"` で囲み、項目を `,` で区切ります。`true` / `false` は小文字です。

| 設定 | 確認する内容 |
| --- | --- |
| `SERVER_URL` | 子機から接続できる親機の HTTPS URL。`127.0.0.1` は親機を指さない |
| `UNIT_NAME` / `UNIT_LOCATION` | 他の子機と区別できる名前、設置場所 |
| `MOTOR_TYPE` | `SERVO` または `STEPPER`。実際のモーターに合わせる |
| `CONTROL_METHOD` | 通常は `RASPI_DIRECT` |
| `USE_SENSOR` | センサーの有無に合わせる |
| `STEPPER_PINS` など | ステッピングモーターを使う場合の GPIO 配線・回転設定 |
| `UNIT_SECRET_FILE` | 通常は `/etc/oiteru/unit-secret` |
| `HEARTBEAT_INTERVAL` | 状態を送る間隔。省略時は 30 秒 |

`UNIT_PASSWORD` を JSON に書かず、次の手順で別ファイルに保存します。
配線や回転量の詳細は [設定項目](configuration.md) を参照してください。

### 2-4. 子機の秘密情報を登録する

この設定作業だけは `sudo` を付けます。

```bash
sudo bash scripts/provision_unit.sh
```

| 質問される内容 | 入力するもの |
| --- | --- |
| `Child device name` | `config.json` と同じ子機名 |
| `Parent URL` | 親機の HTTPS URL |
| `Child device secret` | この子機専用の秘密値。16 文字以上、32 文字以上を推奨。入力中は非表示 |

子機名・接続先・秘密ファイルの場所が `config.json` に反映され、秘密値は `/etc/oiteru/unit-secret` に保存されます。
秘密ファイルの権限は `600` で、この作業をした通常ユーザーが読めるようになります。

**できた目印：** `Provisioning completed.` が表示されます。
内部の疎通確認では、承認前の子機に親機が HTTP 404 を返すことを許容しています。
`Parent authentication check failed` が出た場合は成功ではありません。接続先と通信を確認してください。

### 2-5. 管理画面で子機を承認する

**使うもの：担当者のブラウザ。**

1. 親機の `/admin` にログインする。
2. **子機一覧 → 新規子機の登録**を開く。
3. **自動探知を開始**を押す。
4. 保留中の子機名・接続元 IP・最終通信時刻が、設定した実機と一致するか確認する。
5. 対象の **この子機を登録**を押す。

別の名前や IP の子機を登録せず、設定を確認してください。
候補に出ない場合は親機への疎通を確認し、必要に応じて子機側で 2-4 の確認をやり直します。

### 2-6. 子機を起動する

**実行する場所：子機のプロジェクトフォルダ。通常ユーザーで実行します。**

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh status unit
scripts/tmux_oiteru.sh logs unit
```

`running: oiteru-unit` は tmux の作業画面が存在する目印です。
これだけで正常とは判断せず、ログにリーダー・モーター・通信のエラーがないか確認します。
ログ表示は **Ctrl + C** で終わります。ログ表示を止めても、子機は動き続けます。

親機の **子機一覧**を再読込し、対象子機のオンライン表示と最終接続が更新されることを確認します。
在庫数は実物と合わせ、利用可能状態も確認してください。

tmux は SSH 切断後も動きますが、この手順だけでは子機の OS 再起動後に自動起動しません。
常設運用の自動起動は、設置担当者が [子機の systemd 運用](operations.md#unit-service) を確認して設定します。
既存の systemd 子機を、tmux でも重ねて起動しないでください。

### 2-7. 最後に、一連の操作を確かめる

1. 管理者ログインと親機の応答を確認する。
2. 子機のオンライン表示と実物の在庫を確認する。
3. テスト用カードを登録し、必要な利用許可・残り回数を確認する。
4. 子機で 1 回タッチし、実物が 1 個出ることを確認する。
5. 管理画面で排出結果・利用回数・在庫が反映されたことを確認する。
6. 補充・故障記録・担当者の連絡方法を、後任者と一緒に確認する。

途中で排出結果が不明になった場合は、操作を止めて時刻と子機名を記録し、担当者と調べてください。
