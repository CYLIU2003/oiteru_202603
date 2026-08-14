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

## 回帰確認

<code>tests/test_public_user_flow.py</code> は未ログイン状態で利用者ページと必要な補助 API が管理者ログインへ
リダイレクトされないこと、管理者用の画面・API は引き続き保護されることを確認します。
