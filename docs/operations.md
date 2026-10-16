# OITERU 運用・保守の手順

初めての当番は [QUICK_START.md](../QUICK_START.md) を使ってください。
ここでは在庫修正、故障対応、子機の常設運用、バックアップなど、担当者向けの詳しい手順を説明します。
新規導入は [setup.md](setup.md)、設定値は [configuration.md](configuration.md) が正本です。

## まず、作業する機械と起動方法を確認する

| 対象 | 標準の起動方法 | 状態確認 |
| --- | --- | --- |
| 親機（Linux・MySQL 8） | systemd `oiteru-parent` | 親機で `scripts/parent.sh status` |
| 子機（初回確認） | tmux | 子機で `scripts/tmux_oiteru.sh status unit` |
| 子機（常設・設定済みの場合） | systemd `oiteru-unit` | 子機で `systemctl status oiteru-unit` |

**子機を tmux と systemd で同時に起動しません。** 使用中の方法を [引き継ぎ票](handover.md) に残してください。
親機の起動・停止・復旧は [runbook.md](runbook.md) にまとめています。

<a id="stock"></a>

## 在庫：補充・在庫修正・廃棄

記録の入口は管理画面の **運用管理**（`/admin/operations`）です。
現地の実数を確かめ、対象子機・操作・数量・理由を入力して **在庫操作を登録**を押します。
保存後は「直近の在庫操作」の日時・子機・増減前後・理由を確認します。

| 操作 | 数量 | 例 | 履歴の操作名 |
| --- | --- | --- | --- |
| 補充 | 今回追加した正の数 | `20` で 20 個追加 | `restock` |
| 在庫修正 | 記録との差を符号付きで入力 | 画面 10 個・実物 8 個なら `-2` | `adjustment` |
| 廃棄 | 今回捨てた正の数 | `3` で 3 個減らす | `disposal` |

数量に合計在庫を入れません。0 や、在庫を負数にする操作は受け付けられません。
理由は `定期補充`、`棚卸で数がずれていた`、`破損品を廃棄` など、あとで判断できる内容にします。
利用者の名前・カード番号・連絡先は入れません。

誤入力は、履歴を直接削除・編集せず、実物と最新の記録を確認して新しい修正記録を追加します。
保存エラーや応答の遅れでは、再読込して履歴を確認してから再入力します。
子機詳細の「現在の残り在庫」を変更する方法もありますが、初めての当番は運用管理へ入口を統一します。
子機詳細でも理由の記入が必須で、変更は監査ログに残ります。

## 故障を受付から完了まで追跡する

1. 運用管理の **故障を登録**で、対象子機・分類・状況を入力する。
2. 担当者が決まっていれば選び、わからなければ未割当のまま登録する。
3. 対応開始時に **対応中** に更新する。
4. 実施内容と動作確認を「復旧・対応メモ」に残し、**復旧確認** に更新する。
5. 引き継ぎ・確認が済んだら **完了** に更新する。

```text
受付 → 対応中 → 復旧確認 → 完了
```

復旧確認または完了にするには対応メモが必要です。再発時は「対応を再開」で追跡します。
記録には端末名・時刻・症状・作業内容を残し、利用者情報を入れません。
機器を利用停止にする必要がある場合は、子機詳細の「利用可能状態」も担当者が確認します。
通信断中の子機には画面での変更がすぐ届かないため、現地での停止方法も確認してください。

## 障害時の一次対応

| 症状 | 担当者が確認する順番 |
| --- | --- |
| 管理画面が開かない | 指定ネットワーク・VPN → URL → 親機の `scripts/parent.sh status` |
| ログインできない | ユーザー名・入力 → HTTPS と Cookie の設定 → ログイン試行制限 → 親機ログ |
| 子機がオフライン | 電源 → LAN 等の接続 → 最終接続 → 起動方式に合った子機ログ → 親機 URL |
| 登録用リーダーが未接続 | 親機の USB → `tools/check_nfc_reader.py` → リーダー初期化サービス |
| 排出されない | 実物と画面の在庫 → 利用可能状態・カードの利用条件 → 子機ログ → 配線・センサー・モーター |
| 出たが記録がない | 再タッチや再起動を避け、時刻・子機名・受付番号を保全して履歴とログを照合 |

リーダー診断は、対象機械のプロジェクトフォルダで行います。カード番号は表示しません。

```bash
.venv/bin/python tools/check_nfc_reader.py
```

親機からの DB 接続確認は、接続情報を確認してから行います。
`<MYSQL_USER>` と `<MYSQL_DATABASE>` は実際の値へ置き換え、パスワードはプロンプトで入力します。

```bash
mysql -u <MYSQL_USER> -p <MYSQL_DATABASE> -e "SELECT 1;"
```

<a id="unit-service"></a>

## 子機を systemd で常設運用する

SSH 切断に加え、OS 再起動後や異常終了後も子機を戻す場合は systemd を設定します。
先に [初回セットアップ](setup.md#setup-unit) を完了し、実機で排出・記録を確認してください。
すでにサービス運用中なら新規作成せず、現在の定義を担当者と確認します。

1. 子機で tmux 起動中なら `scripts/tmux_oiteru.sh stop unit` で停止する。
2. `sudo nano /etc/systemd/system/oiteru-unit.service` で、次の定義を保存する。
3. `<子機ユーザー名>` と `<プロジェクトの絶対パス>` を、かっこごと実際の値へ置き換える。

```ini
[Unit]
Description=OITERU Child Device
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=<子機ユーザー名>
WorkingDirectory=<プロジェクトの絶対パス>
Environment=OITERU_STRICT_SECURITY=true
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
Environment=PYTHONIOENCODING=utf-8
Environment=PYTHONUNBUFFERED=1
ExecStart=<プロジェクトの絶対パス>/.venv/bin/python -X utf8 <プロジェクトの絶対パス>/unit.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

例：プロジェクトの絶対パスは `/home/rpi1/oiteru_202603` のような値です。
`User` に root を指定しません。サービスユーザーが秘密ファイルを読め、GPIO・USB を使えることを確認します。
子機は親機の `.env` を読みません。上の定義は親機 URL が HTTPS であることを前提とします。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oiteru-unit
systemctl status oiteru-unit
```

管理画面の最終接続が更新されることを確認し、保守時間に OS 再起動後の復帰も確認します。
その後、この起動方法を引き継ぎ票に記録します。

| 目的 | 子機で実行するコマンド |
| --- | --- |
| 状態 | `systemctl status oiteru-unit` |
| ログ | `sudo journalctl -u oiteru-unit -n 100 -f --no-pager` |
| 再起動 | `sudo systemctl restart oiteru-unit` |
| 一時停止 | `sudo systemctl stop oiteru-unit` |
| 自動起動も停止 | `sudo systemctl disable --now oiteru-unit` |

ログの継続表示は Ctrl + C、`systemctl status` の表示画面は Q で終了します。
連続失敗で起動制限になったときは、原因を修正してから `sudo systemctl reset-failed oiteru-unit` と再起動を行います。
USB・GPIO の権限エラーを、子機の root 起動で回避しないでください。
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

<a id="backup"></a>

## バックアップと復元

Excel のバックアップは利用者データの集計・確認用で、システム全体の復旧用ではありません。
復旧には MySQL 全体の暗号化バックアップを使います。
標準の DB ユーザー権限で実行できるよう、取得スクリプトは `--no-tablespaces` を指定し、
サーバー全体のテーブルスペース情報を取得しません（[MySQL 公式の必要権限](https://dev.mysql.com/doc/refman/8.4/en/mysqldump.html)）。
`.env`、子機の設定・秘密値などは DB に含まれないため、安全な保管先と復旧方法を別途確認します。

**実行する場所：親機のプロジェクトフォルダ。** 鍵は画面に表示せず入力します。

```bash
read -rsp "バックアップ鍵: " OITERU_BACKUP_KEY
printf '\n'
export OITERU_BACKUP_KEY
bash scripts/backup_mysql.sh
unset OITERU_BACKUP_KEY
```

`Encrypted backup created:` と保存先が表示されることを確認します。
標準の保存先は `backups/oiteru-<UTC時刻>.sql.gz.enc` です。
鍵を紛失すると復号できません。ファイルと鍵の保管先、復旧確認の実施日を担当者が管理します。

復元は DB を書き換えます。保守時間を決め、親機・子機の排出と書き込みを止め、対象 DB とファイルを確認します。
通信断だけでは子機がスタンドアロン排出を続ける可能性があるため、現地の停止も確認してください。

```bash
read -rsp "バックアップ鍵: " OITERU_BACKUP_KEY
printf '\n'
export OITERU_BACKUP_KEY
bash scripts/restore_mysql.sh backups/oiteru-<UTC時刻>.sql.gz.enc
unset OITERU_BACKUP_KEY
```

`<UTC時刻>` は実際のファイル名に置き換えます。確認に `RESTORE` の入力を求められます。
管理画面の Excel 復元も既存の利用者データを置き換えるため、補充の誤入力修正には使いません。
復元後は親機の再起動、管理者ログイン、子機 heartbeat、テストカードの排出・履歴を確認して運用へ戻します。

## 設定変更・記録の保全

自動登録モードは標準で無効です。利用上限・期間・自動登録の変更は、実証責任者と確認してから行います。
子機への設定は heartbeat で同期されるため、管理画面で反映完了を確認します。
運用履歴がある子機は削除せず、利用停止にして履歴を保全します。

- `stock_movements` は補充・在庫修正・廃棄の履歴です。直接更新・削除しません。
- `maintenance_tickets` は故障の受付・状態・復旧メモを保持します。
- `admin_audit_logs` は管理者の操作記録です。
- `.env`、秘密値、実 DB、照合表、未送信記録、ログ、バックアップを Git や共有資料へ含めません。
- 外部に利用状況を出す場合は、個人ごとの履歴ではなく集計値を使います。

本番 DB の構造は、親機起動時の migration で管理します。手書き DDL を直接適用しません。
