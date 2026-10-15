# OITERU 取り扱い説明書

OITERU は、NFC カードを使って生理用品を排出し、利用状況・在庫・端末状態を管理するシステムです。
この文書は、学内実証で OITERU を初めて起動する人、日常運用する人、障害時に一次対応する人を対象にしています。

## まず覚える構成

標準構成は次の 2 台です。

~~~text
運用担当者の PC
   │ SSH / ブラウザ
   ├── 親機（Linux・Flask・MySQL 8）
   │      └── 管理画面、利用者登録、履歴、子機との通信
   └── 子機（Raspberry Pi）
          └── NFC リーダー、モーター、センサー、LED
~~~

- 親機は **MySQL 8（InnoDB）** だけを使います。SQLite は廃止しました（`DB_TYPE` が `mysql` 以外だと起動しません）。Docker も使用しません。
- 親機は systemd サービス `oiteru-parent` として自動で起動します。子機は tmux のバックグラウンドセッションで起動します。
- 親機の起動・停止・復旧の短い手順は [docs/runbook.md](docs/runbook.md) にまとめています。
- 親機の管理画面は管理者ログインが必要です。利用者向けの登録・利用状況確認画面はログイン不要です。
- 以下のコマンドは、リポジトリのルートディレクトリで実行します。

この文書では、リポジトリを次の場所に配置したものとして記載します。実際の配置場所が異なる場合は、すべて読み替えてください。

~~~bash
cd ~/Desktop/oiteru_202603
~~~

<親機ユーザー>、<親機ホスト>、<親機URL> など、< > で囲んだ部分は環境に合わせて置き換えます。

## はじめて起動する場合の順番

次の順番で進めると、途中で迷いにくくなります。

1. 親機を準備し、MySQL と親機サービスを起動する
2. 親機の /api/health で起動を確認する
3. 子機を準備し、親機へ接続できる状態にする
4. 管理画面で未登録の子機を承認する
5. 子機を起動し、管理画面でオンラインを確認する
6. テスト用カードで登録・利用状況確認・排出を確認する

## よく使う画面

| 目的 | URL |
|---|---|
| 利用者向けトップ | / |
| 学生証の登録 | /register |
| 利用状況の確認 | /usage |
| 管理者ログイン | /admin |
| 管理者ダッシュボード | /admin/dashboard |
| 子機の確認・登録 | /admin/units |
| 補充・故障対応 | /admin/operations |

---

## 1. 親機を準備する

### 1-1. 親機へ接続する

運用端末から親機へ SSH 接続します。

~~~bash
ssh <親機ユーザー>@<親機ホスト>
cd ~/Desktop/oiteru_202603
~~~

### 1-2. 親機の秘密設定を作る

.env.example をコピーして、親機だけが読める設定ファイルを作成します。

~~~bash
cp .env.example .env
chmod 600 .env
nano .env
~~~

次の値を確認し、change-this-... のまま残さないでください。

| 設定 | 設定内容 |
|---|---|
| SERVER_NAME | 親機の名前（例: OITERU親機） |
| SERVER_LOCATION | 設置場所 |
| FLASK_SECRET_KEY | 32 文字以上のランダムな値。セッション暗号化用 |
| OITERU_ADMIN_USERNAME | 管理画面のログインユーザー名 |
| OITERU_ADMIN_PASSWORD | 管理画面のパスワード。12 文字以上を推奨 |
| CARD_UID_HMAC_KEY | 32 文字以上のランダムな値。カード識別子の保護用 |
| DB_TYPE | mysql |
| MYSQL_HOST | ローカル MySQL なら localhost |
| MYSQL_PORT | 通常は 3306 |
| MYSQL_USER | OITERU 用 MySQL ユーザー |
| MYSQL_PASSWORD | OITERU 用 MySQL パスワード |
| MYSQL_ROOT_PASSWORD | MySQL root 用。ローカル構築スクリプトは sudo mysql を使うため未使用の場合がありますが、設定する場合は必ず変更 |
| MYSQL_DATABASE | 通常は oiteru |

秘密値は、例えば次のコマンドでランダム値を作れます。

~~~bash
openssl rand -hex 32
~~~

標準の HTTPS 運用では、次の設定を維持してください。

~~~dotenv
DB_TYPE=mysql
OITERU_STRICT_SECURITY=true
SESSION_COOKIE_SECURE=true
~~~

ローカルの閉じた検証環境で、http://127.0.0.1:5000 を直接使う場合だけ、次の 2 つを false に変更します。学内実証やネットワーク越しの運用では HTTP を使用しないでください。

~~~dotenv
OITERU_STRICT_SECURITY=false
SESSION_COOKIE_SECURE=false
~~~

### 1-3. Python と MySQL を準備する

~~~bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tmux curl
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
~~~

MySQL がすでにインストール済みの場合は、最後のコマンドから --install を外します。

~~~bash
scripts/setup_local_mysql.sh
~~~

このスクリプトは .env を読み込み、MySQL のサービス起動、データベース作成、OITERU 用ユーザー作成、接続確認を行います。手書き SQL を本番へ直接適用する必要はありません。

### 1-4. 親機を起動する

~~~bash
scripts/parent.sh install
~~~

このコマンドは、親機を systemd サービス `oiteru-parent` として登録し、自動起動を有効にして起動します。`sudo` は付けずに実行し、聞かれたらパスワードを入れます。最後に「問題ありません。」と表示されれば起動しています。以後は PC を再起動しても自動で起動します。API でも確認します。

~~~bash
curl --fail http://127.0.0.1:5000/api/health
~~~

次のような JSON が返れば正常です。

~~~json
{"api_version":"1","deployment_id":"local","service":"oiteru-parent","status":"ok"}
~~~

ブラウザでは、標準 HTTPS の公開 URL を開きます。ローカル URL は、前述のローカル検証用設定に変更した場合だけ使用してください。

~~~text
https://<親機URL>/

# ローカル検証時だけ
http://127.0.0.1:5000/
~~~

### 親機の状態を確認するコマンド

~~~bash
scripts/parent.sh status
scripts/parent.sh logs
~~~

`logs` はログを継続表示します。ログ表示だけを終了する場合は Ctrl-c を押します。親機を停止する場合は、後述の停止コマンドを使います。

---

## 2. Raspberry Pi 子機を準備する

### 2-1. 子機へ接続する

子機上では、通常のログインユーザーで作業します。unit.py は Raspberry Pi 上で root 実行しない構成です。

~~~bash
ssh <子機ユーザー>@<子機ホスト>
cd ~/Desktop/oiteru_202603
~~~

### 2-2. 子機用ソフトウェアをインストールする

~~~bash
chmod +x scripts/setup_unit_environment.sh
./scripts/setup_unit_environment.sh
~~~

このスクリプトは、Python、NFC、I2C、GPIO、tmux などの依存関係、.venv、子機用パッケージを準備します。I2C を新しく有効にした場合は、スクリプトの案内に従って再起動します。

~~~bash
sudo reboot
~~~

再起動した場合は、もう一度 SSH 接続してリポジトリへ移動します。

### 2-3. 子機の公開設定を確認する

セットアップ後に作成された config.json を開き、モーターや配線に関わる項目を実機に合わせます。

~~~bash
nano config.json
~~~

主な設定項目は次のとおりです。

| 設定 | 内容 |
|---|---|
| SERVER_URL | 親機 URL。標準は https://... |
| UNIT_NAME | 子機を識別する名前。例: unit-01 |
| MOTOR_TYPE | SERVO または STEPPER |
| CONTROL_METHOD | 通常は RASPI_DIRECT |
| USE_SENSOR | 排出検知センサーを使うか |
| STEPPER_PINS | ステッピングモーターの BCM GPIO ピン |
| UNIT_LOCATION | 子機の設置場所 |
| HEARTBEAT_INTERVAL | 親機へ状態を送る間隔。通常は 30 秒 |

UNIT_PASSWORD は config.json に書きません。子機の秘密情報は、次の Provisioning 手順で /etc/oiteru/unit-secret に保存します。

### 2-4. 子機の秘密情報を登録する

~~~bash
sudo scripts/provision_unit.sh
~~~

対話形式で次の 3 つを入力します。

1. Child device name: 子機名（config.json の UNIT_NAME と同じ名前）
2. Parent URL: 親機 URL
3. Child device secret: 16 文字以上の子機用秘密情報。32 文字以上を推奨

この処理により、次のファイルが作成されます。

~~~text
config.json                  公開設定（秘密情報は含めない）
/etc/oiteru/unit-secret      子機秘密情報（権限 600）
~~~

完了時に HTTP 404 が表示されても、親機へ接続でき、まだ承認されていない子機として保留された場合は正常です。接続エラーや HTTP 500 の場合は、親機 URL とネットワークを確認してください。

### 2-5. 管理画面で子機を承認する

親機のブラウザで次の操作を行います。

1. https://<親機URL>/admin を開く
2. .env に設定した管理者ユーザー名とパスワードでログインする
3. **子機一覧** → **新規子機の登録** を開く
4. Provisioning の疎通確認で子機が未登録として保留されていることを確認する
5. **自動探知を開始** を押す
6. 子機名、接続元 IP、最終通信時刻が実機と一致することを確認する
7. 対象の **この子機を登録** を押す

名前や IP が実機と異なる場合は登録せず、子機の config.json、接続先、ネットワークを確認してください。

---

## 3. 子機を起動する

子機上で、通常ユーザーとして実行します。

~~~bash
cd ~/Desktop/oiteru_202603
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh status unit
~~~

ログを確認する場合:

~~~bash
scripts/tmux_oiteru.sh logs unit
~~~

標準の HTTPS 構成では、次のエラーが出ていないことを確認します。

- NFC リーダーの初期化エラー
- GPIO / I2C / モーターの設定エラー
- 親機への接続エラー
- heartbeat 送信エラー

親機 URL が http://<親機IP>:5000 の閉じた開発環境の場合だけ、次のように起動できます。学内実証では使用しません。

~~~bash
OITERU_STRICT_SECURITY=false scripts/tmux_oiteru.sh start unit
~~~

親機の管理画面で **子機一覧** を再読込し、対象子機がオンライン、最終接続時刻が更新中、在庫数が正しいことを確認します。

---

## 4. 利用者として操作する

### 4-1. 初めて使う人のカード登録

カード登録は、親機に接続された NFC リーダーを使います。

1. 親機のブラウザで /register を開く
2. NFC リーダーに学生証を置く
3. **IC カードを登録** を押す
4. 登録完了の表示を確認する

親機に NFC リーダーが接続されていない場合は、画面の **再確認** を押してください。登録後も排出できない場合は、管理者が利用許可・利用残数・子機在庫を確認します。

### 4-2. 子機から生理用品を受け取る

1. 子機の待機表示を確認する
2. 学生証を子機の NFC リーダーにかざす
3. 認証と在庫確認が終わるまで、カードを離して待つ
4. 排出が完了してから、次の操作を行う

排出できるかどうかは、次の条件で判定されます。

- カードが登録済みである
- 利用許可が有効である
- 利用者の期間内残数が残っている
- 子機が利用可能で、子機在庫が残っている
- 設定された日・週・月の利用上限に達していない

赤色 LED やエラー表示になった場合は、同じカードを連続して何度もかざさないでください。子機名、発生時刻、画面表示を管理者へ伝えます。

### 4-3. 利用状況を確認する

1. 親機のブラウザで /usage を開く
2. 親機の NFC リーダーに学生証を置く
3. **利用状況を確認** を押す
4. 残り利用回数、利用可否、累計利用回数を確認する

---

## 5. 管理者として日常運用する

### 5-1. 毎日の開始時チェック

親機の管理画面で次を確認します。

1. /api/health が status: ok である
2. **ダッシュボード** で登録ユーザー数、子機数、排出数を確認する
3. **子機一覧** で、利用する子機がオンラインである
4. **運用管理** で「補充必須」「heartbeat 超過」「対応中の故障チケット」を確認する
5. 実際の投入数と画面上の在庫数が一致している

### 5-2. 補充・在庫修正・廃棄を記録する

補充や廃棄は、必ず **運用管理** から記録します。子機詳細画面で残数を直接変更する場合も、理由を入力してください。

| 操作 | 数量の入力 | 例 |
|---|---|---|
| 補充 | 正数 | 20（20 個追加） |
| 在庫修正 | 増減を符号付きで入力 | -2（棚卸差異で 2 個減） |
| 廃棄 | 正数 | 3（3 個廃棄） |

操作手順:

1. **運用管理** を開く
2. 対象子機を選ぶ
3. 操作種別と数量を入力する
4. 理由を入力する（例: 定期補充、棚卸差異、破損品の廃棄）
5. **在庫操作を登録** を押す
6. 直近の在庫操作で、増減前・増減後・理由を確認する

利用者の氏名、カード UID、メールアドレス、電話番号は、在庫理由や運用メモに入力しないでください。

### 5-3. 故障を記録し、復旧まで追跡する

「出ない」「詰まった」「在庫切れ」「通信不良」などは、口頭だけで済ませず **運用管理** に故障チケットを登録します。

1. 対象子機と分類を選ぶ
2. 状況を記入する
3. 必要なら担当者を割り当てる
4. 対応開始時に **対応中** へ変更する
5. 動作確認後、復旧内容をメモして **復旧確認** にする
6. 引き継ぎ・確認が終わったら **完了** にする

基本の状態遷移は次のとおりです。

~~~text
受付 → 対応中 → 復旧確認 → 完了
                  └─ 再発時は対応を再開
~~~

### 5-4. システム設定を変更する

**システム設定** では、次を変更できます。

- 自動登録モード
- 自動登録時の初期残数
- 1 日・1 週間・1 ヶ月あたりの利用上限

標準は **自動登録モード無効** です。無効の場合、未登録カードは利用できません。自動登録を有効にすると、未登録カードが初回利用時に自動登録されるため、実証責任者の承認なしに変更しないでください。

設定変更後は、子機の次回 heartbeat で同期されます。子機一覧で通信と設定反映を確認してください。

### 5-5. 子機を一時停止する

故障、清掃、補充作業などで利用させない場合は、子機詳細の **利用可能状態** を無効にします。履歴がある子機は削除せず、利用停止にして記録を残してください。

---

## 6. 停止・再起動

### 親機

~~~bash
scripts/parent.sh restart              # 再起動
sudo systemctl stop oiteru-parent      # 停止（次に PC を起動したときは自動で起動する）
~~~

親機を再起動した後は、子機の heartbeat が再開してオンラインに戻ることを確認します。保守のために tmux で親機を手動起動する場合は、先に `sudo systemctl stop oiteru-parent` を実行します。手順は [docs/runbook.md](docs/runbook.md) を参照してください。

### 子機（tmux）

#### 実行中か確認する

~~~bash
scripts/tmux_oiteru.sh status
~~~

#### 画面へ再接続する

~~~bash
scripts/tmux_oiteru.sh attach unit
~~~

tmux から離れるだけなら、Ctrl-b を押してから d を押します。これでプロセスを動かしたまま SSH を切断できます。

#### 停止・再起動する

~~~bash
scripts/tmux_oiteru.sh stop unit
scripts/tmux_oiteru.sh restart unit
~~~

#### SSH 接続を切る場合

必ず Ctrl-b → d で tmux から離脱してから SSH を終了します。tmux を使わずに実行中のターミナルを閉じると、親機・子機プロセスも終了することがあります。

---

## 7. バックアップと復元

### 管理画面の Excel バックアップ

管理画面の **バックアップ** は、利用者データを Excel 形式で出力します。日常の集計や確認用に使用してください。

管理画面の **データ復元** は、アップロードした Excel の利用者データで既存の利用者データを置き換えます。実行前に対象ファイルと対象環境を確認してください。

### 復旧用の暗号化 MySQL バックアップ

システム全体の復旧には、暗号化された MySQL ダンプを使います。バックアップ鍵をシェル履歴やチャットへ残さないでください。

~~~bash
read -rsp "バックアップ鍵: " OITERU_BACKUP_KEY
printf '\n'
export OITERU_BACKUP_KEY
scripts/backup_mysql.sh
unset OITERU_BACKUP_KEY
~~~

復元はメンテナンス時間に、対象ファイルを確認してから行います。スクリプトは確認のため RESTORE の入力を求めます。

~~~bash
read -rsp "バックアップ鍵: " OITERU_BACKUP_KEY
printf '\n'
export OITERU_BACKUP_KEY
scripts/restore_mysql.sh backups/oiteru-<UTC時刻>.sql.gz.enc
unset OITERU_BACKUP_KEY
~~~

復元後は、親機の起動、管理者ログイン、子機 heartbeat、テストカードでの排出状態を確認してから運用へ戻します。

---

## 8. 困ったときの確認順

### 親機が起動しない

症状ごとの対処表は [docs/runbook.md](docs/runbook.md) にあります。

~~~bash
scripts/parent.sh status
scripts/parent.sh logs
~~~

次も確認します。

- .env が存在するか
- DB_TYPE=mysql になっているか
- MYSQL_PASSWORD が change-this-... のままではないか
- FLASK_SECRET_KEY、CARD_UID_HMAC_KEY が 32 文字以上か
- MySQL の接続情報が正しいか

接続だけ確認する場合:

~~~bash
mysql -u <MYSQL_USER> -p <MYSQL_DATABASE> -e "SELECT 1;"
~~~

### 管理画面へログインできない

- .env の OITERU_ADMIN_USERNAME と OITERU_ADMIN_PASSWORD を確認する
- HTTPS 運用では SESSION_COOKIE_SECURE=true を維持する
- ローカル HTTP 検証では OITERU_STRICT_SECURITY=false と SESSION_COOKIE_SECURE=false にして親機を再起動する
- ログインに 5 回失敗すると、設定された時間（標準 900 秒）ブロックされるため、待ってから再試行する
- FLASK_SECRET_KEY を運用中に変更しない。変更すると既存の管理者セッションが無効になる

### 子機が未登録・オフラインになる

子機側:

~~~bash
scripts/tmux_oiteru.sh status unit
scripts/tmux_oiteru.sh logs unit
curl --fail <親機URL>/api/health
~~~

次を確認します。

- config.json の SERVER_URL と UNIT_NAME
- /etc/oiteru/unit-secret が存在し、子機ユーザーが読めること
- 親機と子機が同じ到達可能なネットワークにいること
- 子機を root で起動していないこと
- 管理画面の **新規子機の登録** で承認済みであること

Provisioning 時の 404 / Unit not registered は、承認前であれば正常です。接続エラーや認証エラーは正常ではありません。

### NFC リーダーが認識されない

親機または子機で次を確認します。

~~~bash
lsusb
systemctl status pcscd
sudo systemctl restart pcscd
~~~

親機に接続されたリーダーは、次でも確認できます。

~~~bash
curl http://127.0.0.1:5000/api/local_nfc_reader
~~~

USB リーダーを抜き差ししてから、親機または子機を再起動すると改善する場合があります。NFC リーダーを認識できないままカード操作を繰り返さないでください。

### 排出されない・排出結果が不明

1. 管理画面で子機在庫と利用可能状態を確認する
2. 利用者の登録状態、利用許可、期間内残数、利用上限を確認する
3. 子機ログで NFC、モーター、センサー、親機通信のエラーを確認する
4. 電源、配線、詰まり、排出検知センサーを確認する
5. 発生時刻と子機名を故障チケットへ記録する

物理的には排出されたのに画面や履歴が更新されない場合、同じカードを再度かざしたり、在庫を手計算で二重に減らしたりしないでください。イベント ID と発生時刻を保全して、運用責任者が履歴とログを照合します。

---

## 9. セキュリティと取り扱い上の注意

- .env、config.json、/etc/oiteru/unit-secret、logs/、バックアップファイルを Git に追加しない。
- 管理者パスワード、MySQL パスワード、子機秘密情報を共有チャットや資料へ貼り付けない。
- ネットワーク越しの親機・子機通信は HTTPS を使用する。
- 管理画面の在庫理由、故障状況、復旧メモに、氏名・カード UID・連絡先を記録しない。
- スクリーンショットやログを共有するときは、カード識別子、IP アドレス、認証情報を隠す。
- 物理排出の結果が不明なときは、二重排出防止のため操作を止め、時刻・端末・表示を記録する。

## 関連資料

- [全体概要（README）](README.md)
- [日常運用・障害対応](docs/operations.md)
- [利用者と管理者の画面フロー](docs/user_flow.md)
- [子機セットアップ詳細](scripts/SETUP_UNIT.md)
- [子機・従親機の設定項目](config_templates/README.md)
- [Windows の NFC リーダー設定](docs/card_reader_windows.md)

このファイルを、親機・子機の初回構築と日常操作の入口として使用してください。
