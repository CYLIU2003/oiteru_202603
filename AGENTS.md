# OITERU AGENT RULES

## プロジェクト目的
OITERU は、NFC カードを用いて生理用品を管理・排出し、利用履歴と端末状態を扱う IoT システムである。
本プロジェクトの改修では、単なる試作コードではなく、学内実証で安定運用できる構成を目指す。

---

## 最優先方針
1. 見た目や新機能より、認証・DB・ログ・障害時整合性を優先する。
2. SQLite 前提の実装は段階的に廃止し、標準DBは MySQL 8(InnoDB) とする。
3. 既存機能を壊さないよう、小さな PR 単位で変更する。
4. Raspberry Pi 実機依存部分は必ず抽象化し、モックでテスト可能にする。
5. README / docs / config example は実装と同時に更新する。

---

## DB 方針
- 標準DBは MySQL 8(InnoDB)。
- SQLite は開発・本番の標準構成としては使用しない。
- SQLite 互換コードは `legacy/` へ隔離するか、不要なら削除する。
- DB 接続設定は `.env` ベースに統一する。
- スキーマ変更は migration 管理する。
- 手書きDDLの直接本番反映は禁止。migration を通すこと。

---

## 必須ディレクトリ責務
- `app/api/`: HTTP ルーティング、入力検証、レスポンス整形
- `app/services/`: 業務ロジック
- `app/repositories/`: DBアクセス
- `app/models/`: ORMモデル、DTO、schema
- `app/auth/`: 認証、セッション、権限制御
- `unit/device/`: 端末ハード制御
- `unit/client/`: 親機API通信
- `tests/`: 単体テスト・統合テスト
- `docs/`: 運用資料、構成図、障害時対応

禁止事項:
- route handler から直接 SQL を書かない
- template/UI 層から直接 DB 操作しない
- 実機GPIO/NFC処理を業務ロジック層へ直書きしない

---

## DB スキーマ原則
最低限、以下の責務は分けること。
- `admin_users`: 管理者
- `users`: 利用者情報
- `cards`: カード識別子
- `devices`: 子機/端末
- `dispense_events`: 排出イベント
- `device_status_logs`: 端末状態ログ

原則:
- 個人情報と排出履歴は分離
- すべての主要テーブルに `created_at`, `updated_at` を持たせる
- 必要に応じて `deleted_at` または `is_active` を持たせる
- foreign key と index を明示する
- カードUIDは必要ならそのまま保存せず、ハッシュ化や擬似ID化を検討する

---

## 排出処理の状態管理
排出処理は単発の if 文で済ませず、状態遷移を明示すること。

推奨状態:
- `requested`
- `authorized`
- `dispensing`
- `dispensed`
- `recorded`
- `failed`

要件:
- 冪等性を持たせる
- 二重排出を防ぐ
- 物理排出済みだがDB未反映、を追跡可能にする
- 失敗理由は機械可読なコードで残す

---

## 認証・セキュリティ
- 管理者パスワードの直書き禁止
- 平文パスワード保存禁止
- セッション期限必須
- ログイン試行制限を設ける
- 機微情報はログへ平文出力しない
- `.env`, secrets, 実DB は Git 管理しない

---

## ログ方針
- `print()` ではなく logger を使う
- レベルは `INFO`, `WARNING`, `ERROR` を最低限分ける
- ユーザー名、カードUID、トークン、パスワードはマスキング
- ログは event_id / device_id 中心で追えるようにする
- ローテーション可能な形にする

---

## API 設計ルール
- API は `/api/v1/...` に統一する
- エラー形式を統一する
- 成功/失敗を JSON で明示する
- 入出力 schema を定義する
- 端末APIと管理APIを分離する

推奨例:
- `POST /api/v1/auth/card-scan`
- `POST /api/v1/dispense/request`
- `POST /api/v1/dispense/result`
- `POST /api/v1/devices/heartbeat`
- `GET /api/v1/admin/stats`

---

## テストルール
最低限、以下をテスト対象とする。
- ログイン
- カード認証
- 利用可否判定
- 排出イベント作成
- API 正常系
- API 異常系
- DB repository

実機依存コードは interface を切り、mock 実装でテスト可能にすること。

---

## 変更時の必須更新
コード変更時は、必要に応じて必ず以下も更新する。
- `README.md`
- `QUICK_START.md`
- `.env.example`
- migration
- `docs/` の運用説明

---

## PR の粒度
1 PR 1目的を原則とする。
好ましい粒度:
- 認証修正だけ
- DB migration 追加だけ
- SQLite 廃止だけ
- heartbeat API 追加だけ

避ける:
- 認証変更 + DB 全変更 + UI 改修を同時に行う巨大PR

---

## 優先実装順
1. SQLite / 実DB / ログの除外
2. 管理画面認証強化
3. MySQL 標準化
4. DB スキーマ再設計
5. 排出イベント状態管理
6. 責務分離
7. テスト導入
8. heartbeat / 監視
9. 権限制御
10. UI/UX 改善

---

## 完成条件
- MySQL を標準DBとして起動できる
- SQLite なしでも一連の操作が通る
- 管理画面の固定認証情報が消えている
- 排出イベントが追跡可能
- docs を見れば第三者が再現・運用できる


## 重要
Claude codeとマサチューセッツ工科大でAmazonにいる超優秀なエンジニアにもレビューしてもらいます