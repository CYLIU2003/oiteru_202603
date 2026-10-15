# OITERU 運用手順

この文書は、OITERU を学内実証で引き継ぐための運用手順です。開発手順ではなく、日常運用と障害時対応を対象にします。

## 標準構成

| 項目 | 標準 |
|---|---|
| 親機 | `db_server.py` |
| DB | ローカル MySQL 8 (InnoDB) |
| 子機 | Raspberry Pi / Linux + `unit.py` |
| 親機の起動 | systemd サービス `oiteru-parent`（導入: `scripts/parent.sh install`） |
| 子機の起動 | `tmux`（`scripts/tmux_oiteru.sh`）または systemd `oiteru-unit.service` |

Docker は当面の標準運用では使いません。MySQL は OS の `mysql` サービスとして起動します。

## 日常運用

- 補充前に管理画面で対象子機の在庫と最終接続時刻を確認する
- 補充後は `初期在庫数` と `現在の残り在庫` を更新する
- 子機設定を変えた場合は、設定送信後に heartbeat 同期完了を確認する
- 管理画面の初期認証情報は `.env` の `OITERU_ADMIN_USERNAME` / `OITERU_ADMIN_PASSWORD` で管理し、共有チャットに平文で貼らない
- 運用ログやカード UID を画面共有・資料貼り付けに使わない

## 起動・停止

親機は systemd で自動起動します。起動・停止・復旧の手順は [runbook.md](runbook.md) を参照してください。

```bash
scripts/parent.sh status
scripts/parent.sh restart
```

子機:

```bash
cd ~/Desktop/oiteru_202603
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

状態確認:

```bash
scripts/parent.sh status
scripts/tmux_oiteru.sh status unit
```

## ラズパイ子機の systemd サービス運用（2026-08-14 実績: rpi1)

学内実証で SSH が切れても子機が動き続けるようにするため、systemd サービス化を推奨します。
`rpi1`（Raspberry Pi 5 / Debian 13 trixie）では以下の構成で稼働確認済みです。

### サービス定義 `/etc/systemd/system/oiteru-unit.service` の要点

- `User=rpi1` **必須**: `unit_client.py` は root 実行を拒否する設計（`PLATFORM == "RASPI"` かつ `geteuid() == 0` で exit 1）
- `Environment=OITERU_STRICT_SECURITY=false`: 親機 URL が HTTP の場合に必要（HTTPS 化すれば不要にできる）
- `Environment=LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1` + `ExecStart=... python -X utf8 ...`: systemd 環境では LANG 未設定だと Python 出力が euc_jp になり、絵文字を含む print で UnicodeEncodeError になるため
- `Restart=always`: 異常終了時は自動再起動

```ini
[Service]
Type=simple
User=rpi1
Group=rpi1
WorkingDirectory=/home/rpi1/Desktop/oiteru_202603
Environment=OITERU_STRICT_SECURITY=false
Environment=LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
ExecStart=/home/rpi1/Desktop/oiteru_202603/.venv/bin/python -X utf8 /home/rpi1/Desktop/oiteru_202603/unit.py
Restart=always
RestartSec=10s
```

### 運用コマンド

```bash
sudo systemctl enable --now oiteru-unit.service   # 有効化・起動
sudo systemctl restart oiteru-unit.service        # 再起動
sudo systemctl status oiteru-unit.service         # 状態確認
sudo journalctl -u oiteru-unit.service -f         # ログ確認（制御文字が混ざる場合は --output=cat | sed 's/\x1b\[[0-9;]*m//g'）
```

### 注意点

- `Restart=always` で 5 回以上連続失敗すると systemd が再起動をブロックする（`Start request repeated too quickly`）。
  設定変更後は必ず `sudo systemctl reset-failed oiteru-unit.service` を実行してから `restart` すること。
- NFC リーダー（Sony RC-S380）を一般ユーザーで使うには udev ルールが必要:
  `/etc/udev/rules.d/99-sony-rcs380.rules` に
  `SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="06c1", MODE="0666", GROUP="plugdev"`
  ※ idProduct は実機の lsusb で確認（rpi1 は 06c1）。既存のデバイスノードには反映されないため、
  接続中の場合は `sudo chmod 666 /dev/bus/usb/001/007` で即時適用する。
- 子機の `OITERU_STRICT_SECURITY` は `unit_client.py` が環境変数から直接読む（`.env` は子機では読み込まれない）。
## バックアップと復元

Excel出力は管理用の集計に限定し、復旧用には MySQL 全体の暗号化 dump を使います。
バックアップ鍵は `.env` に保存せず、保護された環境変数から渡します。

```bash
OITERU_BACKUP_KEY='十分に長いバックアップ鍵' scripts/backup_mysql.sh
OITERU_BACKUP_KEY='同じ鍵' scripts/restore_mysql.sh backups/oiteru-<UTC時刻>.sql.gz.enc
```

復元はメンテナンス時間中にのみ実施し、復元後には親機 bootstrap・管理者ログイン・
子機 heartbeat・架空カードでの排出状態遷移を確認してください。

## スタンドアロンモード（親機が止まっても子機が排出を続ける）

親機に接続できないとき、子機は最後に受け取った **照合表（offline cache）** を使い、子機だけで
排出を判断します。排出の記録は子機に保存され、親機が復旧すると自動で送信・反映されます。

### 動き

1. 親機が動いている間、子機は heartbeat のたびに未送信の記録を送り、約 10 分ごとに照合表を更新する
   （`POST /api/v1/units/offline-cache`）。照合表には「利用許可があり、今の期間にまだ使えるカード」と
   回数だけが入る（カードは card ref＝ハッシュ値。生の UID は入らない）
2. 子機が `/api/record_usage` に接続できない（接続エラー・タイムアウト）と、照合表で判断して排出する
3. 排出したら、すぐに子機の `data/offline/queue.jsonl` に追記する（電源断でも残る）
4. 親機が戻ると `POST /api/v1/units/offline-events` で送信する。`event_id` が一意なので、
   同じ記録を何度送っても 1 回しか数えない
5. 親機は記録を排出時刻（`occurred_at`）で保存し（`source = 'offline'`）、利用者の残数と子機の在庫を減らす

オンラインで認可された排出の「結果」だけが親機に届かなかった場合も、子機が保存して後で送り直します。

### 子機だけで排出してよい条件（すべて満たすとき）

| 条件 | 既定値 | 設定場所 |
|---|---|---|
| スタンドアロンモードが有効 | 有効 | 親機 `.env` の `OITERU_OFFLINE_MODE`、子機 `config.json` の `OFFLINE_MODE_ENABLED` |
| 照合表が新しい | 72 時間以内 | 親機 `OITERU_OFFLINE_CACHE_MAX_AGE_HOURS` |
| カードが照合表にある | 利用許可あり・残数あり・期間上限内 | 親機の利用者データ |
| そのカードのオフライン利用回数 | 1 枚につき 1 個まで | 親機 `OITERU_OFFLINE_PER_CARD_LIMIT` |
| 未送信の記録の件数 | 300 件まで | 親機 `OITERU_OFFLINE_MAX_EVENTS` |
| 子機の在庫 | 0 より多い | 親機の在庫（heartbeat で受信） |

未登録カードの自動登録は、オフライン中は行いません（親機が UID を受け取れないため）。

### 同期後の確認

- 管理画面の履歴に `オフライン利用を同期` と出る
- 次のコードが付いた記録は「排出は済んだが親機の帳簿と合わなかった」ものです。削除せず、運用責任者が確認します

| error_code | 意味 |
|---|---|
| `OFFLINE_LIMIT_OVERRUN` | 同期時点で利用者の残数が 0 だった（オフライン中に他の子機でも使った等） |
| `OFFLINE_UNIT_STOCK_MISMATCH` | 同期時点で親機上の子機在庫が 0 だった（在庫数のずれ。棚卸しで修正） |
| `OFFLINE_USER_UNKNOWN` | オフライン中に利用者が削除された |

### セキュリティ上の注意

照合表には、UID からハッシュ値を作るための鍵（`CARD_UID_HMAC_KEY` の値）が入ります。
子機が盗まれた場合はこの鍵が漏れたものとして扱い、鍵を変更してください（変更すると全利用者の
再登録が必要になるため、変更手順は運用責任者が判断します）。照合表と記録のファイルは
所有者だけが読める権限（0600）で保存されます。

## 障害時の一次対応

### 管理画面に入れない

- `.env` の `OITERU_ADMIN_USERNAME` と `OITERU_ADMIN_PASSWORD` が正しいか確認する
- 親機再起動後に `FLASK_SECRET_KEY` が変わっていないか確認する
- ログイン試行上限に達した場合は、待機後に再試行する
- 親機が起動しているか `scripts/parent.sh status` で確認する

### 子機がオフライン

- 子機本体の電源、LAN/Tailscale、NFC リーダー接続を確認する
- 管理画面で `最終接続` を確認する
- 子機側で `scripts/tmux_oiteru.sh status unit` を確認する
- `config.json` の `SERVER_URL` が親機 IP を指しているか確認する
- 子機から `curl https://<親機ホスト名>/api/health` を実行する

### 排出されない

- 子機在庫が 0 でないか確認する
- センサー詰まり、モーター配線、電源を確認する
- ステッピング子機は `config.json` の `STEPPER_PINS`, `STEPPER_PHASE_ORDER`, `STEPPER_BACKEND` を確認する
- CUI 設定メニューの `t` / `r` でステッパー単体テストを行う
- 子機ログと heartbeat の直近時刻を確認する
- 同一カードの短時間連打でないか確認する
- 物理排出済みだが DB 未反映の疑いがある場合は、時刻、子機名、カード操作の有無をメモしてから調査する

### DB 接続異常

- `systemctl status mysql` で MySQL サービス状態を確認する
- `.env` の `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` を確認する
- 親機から次を実行する

```bash
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
```

- 初回構築直後なら `scripts/setup_local_mysql.sh` を再確認する

## 親機の NFC リーダー（カード登録用）

親機 PC に NFC リーダー（Sony PaSoRi RC-S380 推奨）を接続すると、管理画面・登録ページからカードを直接読み取って利用者登録できます。

### 動作確認

```bash
# リーダー検出のみ
python tools/check_nfc_reader.py

# カードを1枚読み取る（10秒待機）
python tools/check_nfc_reader.py --read
```

診断ツールは成功時に終了コード `0`、未検出・読み取り失敗時に `1` を返します。
カード UID と例外の詳細文字列は出力せず、成功の有無とエラー種別のみ記録します。

### Windows 固有の注意

- `server.py` の NFC 読み取りは nfcpy（libusb 経由）を使います。`pip install libusb` を入れておくと nfcpy が DLL を自動で見つけます。
- リーダーが Windows に認識されない場合は、USB ポートの挿し直し・別ポートを試します。
- デバイスマネージャーで「その他のデバイス」に出る場合、Zadig (https://zadig.akeo.ie) で当該デバイスに **WinUSB** ドライバを割り当ててください（Sony 公式 PC/SC ドライバが入っていると libusb から使えないため注意）。
- Linux ではリーダーを挿すだけで認識され、`libusb` パッケージのみ必要です。

## プライバシー運用

- `.env`, `config.json`, `logs/`, `*.log`, `*.sqlite3`, バックアップファイルは Git に含めない
- 利用履歴を外部共有する場合は、個票ではなく集計値を使う
- ユーザー名、カード UID、トークン、パスワードをログや資料に平文で出さない
- スクリーンショットを共有する場合は、カード ID と認証情報を隠す

## 日常運用: 補充・故障対応

管理画面の **運用管理**（/admin/operations）を、補充・在庫修正・廃棄・故障対応の
唯一の記録入口として使います。利用者のカード UID や個人別利用履歴を、この画面で確認する
必要はありません。

### 開始時の確認

1. 「補充必須（在庫 0）」を確認し、対象端末を選ぶ。
2. 「heartbeat 超過」を確認する。ここでは既存の監視と同じ **60 秒** を表示基準とする。
   60 秒は初期の監視基準であり、端末ごとの heartbeat 間隔を変える場合は運用責任者が
   基準を見直す。
3. 「対応中・復旧確認のチケット」を確認し、同じ端末に未処理の事象がないか見る。

### 補充・在庫修正・廃棄

1. 対象端末を選び、操作種別（補充 / 在庫修正 / 廃棄）と数量を入力する。
2. 理由には「定期補充」「棚卸差異」「破損品の廃棄」など、後から判断できる内容を記す。
3. 保存後、「直近の在庫操作」で **増減前・増減後・理由** を確認する。

補充は正数、廃棄は正数（システムが減算として記録）、在庫修正は増減を符号付きで入力します。
在庫を負数にする操作は拒否されます。排出処理と同時に在庫が変化した場合も、古い値で上書き
せず、画面を再読込してから記録し直します。

子機詳細画面から在庫数を変更する場合も、理由の入力が必須です。保存された変更は
stock_movements と管理者監査ログの両方に記録されます。

### 故障チケット

1. 故障を見つけたら、対象端末・分類（在庫切れ / 詰まり / 機器故障 / 通信不良 / その他）・担当者・状況を登録する。
2. 対応を始めたら **対応中** に更新する。
3. 動作確認ができたら、実施内容を「復旧・対応メモ」に残して **復旧確認** に更新する。
4. 引継ぎまたは確認が済んだら **完了** にする。再発時は **対応を再開** して同じチケットを追跡する。

状態遷移は「受付 → 対応中 → 復旧確認 → 完了」を基本とします。復旧確認または完了には、
何を確認・修復したかを必ず残します。

### 記録してはいけないもの

在庫理由、故障状況、復旧メモには、利用者の氏名、カード UID、メールアドレス、電話番号を
入力しません。運用記録は端末・時刻・作業内容だけで完結させます。

### 利用者からの匿名報告

匿名の「出ない・詰まった・空」報告は有効な次段階の改善候補ですが、公開入力にはレート制限、
悪用対策、掲示場所の運用責任者が必要です。これらが未決定の間は公開 API を設けず、運用担当者が
故障チケットとして登録してください。

## 運用データと復旧

- stock_movements は補充・在庫修正・廃棄の不変履歴です。内容を直接更新・削除しません。
- maintenance_tickets は故障の受付、状態、復旧メモを保持します。
- admin_audit_logs は管理者の操作証跡です。
- 運用履歴がある子機は削除せず、利用停止にして履歴を保全します。

MySQL のバックアップ・復元時には、これらの表も通常の DB バックアップに含まれます。手書き
DDL で本番 DB を変更せず、アプリケーション起動時の migration 010_add_operations_management
で作成されることを確認してください。

## 引き継ぎ時チェックリスト

- `.env.example` を元に新しい `.env` を作成した
- `config.example.json` を元に各子機の `config.json` を作成した
- `scripts/setup_local_mysql.sh` でローカル MySQL を準備した
- `scripts/parent.sh install` で親機を systemd に登録し、起動した
- 後任者に [runbook.md](runbook.md) の「はじめての人へ」を一緒にやってもらった
- 管理画面ログインを確認した
- 子機 heartbeat を確認した
- 補充手順と障害時一次対応を担当者へ説明した

最終更新: 2026-08-11
