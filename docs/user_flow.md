# 利用者・管理者の画面フロー

## 方針

利用者がメイン画面から使う機能は、管理者ログインを必要としません。管理者ログインは、
利用者情報、端末設定、在庫、運用記録、バックアップを扱う操作だけに限定します。

~~~mermaid
flowchart TD
    home["/ メイン画面<br/>ログイン不要"]
    register["/register<br/>学生証の登録"]
    usage["/usage<br/>利用状況の確認"]
    read_card["/api/read_card<br/>ローカル NFC 読取"]
    result["登録完了または利用状況の結果"]
    admin_login["/admin<br/>管理者ログイン"]
    admin["/admin/* と /api/v1/admin/*<br/>設定・在庫・履歴・運用管理"]

    home --> register
    home --> usage
    register --> read_card
    usage --> read_card
    read_card --> result
    home --> admin_login
    admin_login --> admin
~~~

## アクセス境界

| 区分 | 画面・API | 認証 |
|---|---|---|
| 利用者 | <code>/</code>、<code>/register</code>、<code>/usage</code> | 不要 |
| 利用者画面の補助 | <code>/api/read_card</code>、<code>/api/local_nfc_reader</code>、<code>/api/reader_status</code> | 不要 |
| 管理者 | <code>/admin/*</code>、<code>/api/v1/admin/*</code>、利用者一覧・端末設定・バックアップ API | 管理者ログイン必須 |

利用者用の公開 API は、画面表示とローカル NFC 読取に必要な最小限に限定します。
利用者一覧、保存済みのカード情報、在庫変更、端末設定、運用チケットを公開 API に追加してはいけません。

## 利用者フロー

1. 利用者は <code>/</code> を開く。ログイン画面を通る必要はない。
2. 新規利用者は <code>/register</code> でローカル NFC リーダーに学生証をタッチする。
3. 利用状況を確認する利用者は <code>/usage</code> で学生証をタッチする。
4. リーダー未接続時は、その画面で接続状態を案内し、再確認できる。管理者ログインへ遷移させない。
5. 未登録カードは、<code>auto_register_mode</code> が有効な場合だけ既存の自動登録フローへ進む。無効な場合は未登録として案内する。

## 管理者フロー

管理者だけが <code>/admin</code> からログインし、ダッシュボード、端末設定、利用者管理、補充・故障対応、
バックアップを扱います。利用者フローから管理者 API を呼び出したり、利用者の操作を理由に
管理者ログインへリダイレクトしたりしません。

## 登録画面のデザイン

`/register` は [Google Labs DESIGN.md](https://github.com/google-labs-code/design.md) の形式に沿った
[`DESIGN.md`](../DESIGN.md) を基準にしています。濃紺の案内パネルと白い操作パネル、
落ち着いた背景、システムの日本語フォントで構成し、登録ボタンを主操作として強調します。
大学の公式ロゴを維持し、接続状態と日時をヘッダーに小さく表示します。
時計は閲覧端末のローカル日時を使い、日付・曜日と時分秒を1秒ごとに更新します。
ヘッダーの「生理用品配布」は丸ゴシックの Kosugi Maru Regular を使用します。
Google Fontsから取得した表示6文字分のフォントを `static/fonts/kosugi-maru-service.ttf`
としてローカル配信し、Apache 2.0ライセンスは同ディレクトリの `LICENSE-KosugiMaru.txt` に同梱しています。
このラベルの文字を変更する場合はフォントのサブセットも更新してください。
画面幅720px以下では1列にし、装飾のカード図を省略します。
説明は「学生証を用意する」「リーダーに置く」「登録する」の3手順と各1行程度の補足で構成し、接続状態と必要な対処を短く表示します。
専用CSSは `static/css/register.css`、テンプレートは `templates/register.html` です。
共通テンプレートの表示ブロックで切り替え、他画面には専用CSSを読み込みません。

ロゴは2026-09-06に[公式ヘッダーロゴ](https://www.tcu.ac.jp/tcucms/wp-content/themes/tcu/assets/img/shared/header_logo.svg)
を取得し、改変せず `static/img/tcu-header-logo.svg` に保存しています。ロゴの取得元は東京都市大学です。
ロゴはローカル配信するため、表示時に大学サイトへの接続は不要です。
接続確認済みの場合は既存のPOST登録、未接続の場合はGET再確認を使います。
登録ボタンが表示されるかどうかはページ読み込み時の判定です。接続後は再確認してください。

デザイン定義は `node node_modules/@google/design.md/dist/index.js lint DESIGN.md` で検証できます
（依存パッケージが未導入の場合は `npm ci`）。PCでは1366×768で登録ボタンまで見えること、
モバイルでは320px幅でも横スクロールがないこと、接続・未接続の両状態を確認します。

## 回帰確認

<code>tests/test_public_user_flow.py</code> は未ログイン状態で利用者ページと必要な補助 API が管理者ログインへ
リダイレクトされないこと、管理者用の画面・API は引き続き保護されることを確認します。
