# Codex への状況報告・相談プロンプト（第2版 2026-08-14）

## あなたへの依頼
OITERUシステム（NFCカードで生理用品を排出するIoTシステム）の実機動作確認を進めています。
前回のレビュー（SHA-256直接保存の危険性・正規登録推奨）は**反映済み**です。その後の進展で**新しいブロッカー（親機起動不可）**が発生しました。以下の状況を読み、**①新しい障害の根本原因**、**②復旧の最善手**、**③安全な代替案**をコードベースを読んで評価してください。**コードを書く必要はありません。調査と方針提案のみ**です。

## ゴール（未達）
1. 親機（hirameki-3, Ubuntu 26.04 + MySQL）起動 ← **現在ここで失敗中（新ブロッカー）**
2. 子機 RP1（rpi1, Raspberry Pi）を親機に登録してオンライン化（DB登録は完了、heartbeat認証は成功済み）
3. RP1 上でステッピングモーター単体テスト（CUI の t/r/off コマンド）
4. NFC 含む全体テスト（カード認証 → 排出 → 履歴更新）

## 環境
| マシン | SSHホスト | プロジェクトパス | git HEAD |
|---|---|---|---|
| 親機 | hirameki-3 | `/home/hirameki-3/デスクトップ/oiteru_202603` | 9d1df41（origin/main と一致） |
| 子機 | rpi1 | `~/Desktop/oiteru_202603` | 5846e6b（古い） |
| 開発機 | (Windows) | `C:\oiteru_202603` | 53bc6ff |

- 親機は `scripts/tmux_oiteru.sh start parent` → `venv-start.sh parent-mysql` → `db_server.py`（MySQL強制）→ `server.py` を実行。ポート5000、単一プロセス。
- 親機は最初 **16:23 に正常起動**し `/api/health` が `{"server":"oiteru","status":"ok"}` を返していた。

---

## 🔴 ブロッカーA（最新・最重要）: 親機が再起動できない

### 時系列
- **16:23** — 初回起動成功。health OK。rp1 のDB登録・heartbeat認証（HTTP 200 ×3）も成功。
- **18:04頃** — 親機の Flask プロセス・tmux セッションが**消失**（原因不明）。MySQL は稼働継続、OS再起動なし、ディスク余裕あり。
- **18:05-18:06** — `tmux_oiteru.sh start parent` で再起動を試みる → **即死**。
  - ログ: `OITERU_STRICT_SECURITY では SESSION_COOKIE_SECURE=true が必要です。`（error）
  - ログ: `CARD_UID_HMAC_KEY が未設定・既定値・短すぎる値です（32文字以上必須）。`（error）
  - → 「セキュリティ設定エラーにより起動を停止しました」

### 矛盾点（要調査）
- `.env` の実値（マスク確認）: `OITERU_STRICT_SECURITY=false`、`SESSION_COOKIE_SECURE=false`、`CARD_UID_HMAC_KEY` は長さ64。→ **検証を通過するはず**
- にもかかわらず strict エラーが出る → `OITERU_STRICT_SECURITY` が **true として評価**されている。
- `.env` の mtime は **18:05:31**（最初の調査時 16:xx には存在しなかった `CARD_UID_HMAC_KEY` が追加されている）。**誰が変更したか不明**（別エージェント or ユーザー手動 or 何かの同期）。
- 検証コード: `app/auth/auth_manager.py:180-230` の `validate_runtime_security()`。`strict` フラグがどこから来るか（server.py の起動検証 2780-2840 行）**未確認**。
- `server.py` に `load_dotenv` の呼び出しが**無い**。python-dotenv も**未インストール**（pip show 空）。→ `.env` がどう Python プロセスに渡っているのか不明（tmux 起動時に source している？ shell の export？）。

### 確認済みの関連事実
- `server.py:103-104`: `SESSION_COOKIE_SECURE` は `os.getenv(...)` で読む。
- `auth_manager.py:200`: `if strict and os.getenv("SESSION_COOKIE_SECURE","false").lower() != "true"` → error。
- `auth_manager.py:209-216`: `CARD_UID_HMAC_KEY` は `strict` のとき error、非strictなら warning。
- つまり **strict=true なら両方error** になる。.env が false なのに strict=true になる理由が謎。

---

## 🟠 ブロッカーB: 親機ダウンの原因不明
- 16:23 稼働 → 18:04 消失。クラッシュログ（journald や logs/oiteru-parent.log の末尾）**未確認**。
- tmux セッションごと消えている → `kill` された？ クラッシュ？ OOM？
- 再起動を繰り返すと logs/oiteru-parent.log にエラーが追記される（18:04→18:05→18:06 の3回分）。

---

## 🟡 C: RP1 の heartbeat 結果（親機ダウン前の成功記録）
- **17:48:01** — unit サービス起動。診断: GPIO OK / 親機接続OK / NFC検出 / Stepper backends `PigpioZero=NG, RpiMotorLib=OK, GPIO=OK`。
- **17:48:02** — 「在庫: 10」表示 = heartbeat 認証成功（**1回のみ**）。
- **17:48:32以降** — 「在庫: --- (サーバーエラー)」連続。親機ダウンが原因の可能性が高いが、認証問題の可能性も残る。
- **手動再現テスト（18:0x）**: RP1 から `load_config()`（= unit/configuration.py 経由、UNIT_SECRET_FILE 読み込み確認済み、秘密len=32）で secret を取得 → heartbeat 送信 → **Connection refused**（親機ダウンが原因）。
- つまり **RP1側の認証実装は正しい可能性が高い**（secret は `/etc/oiteru/unit-secret` から読める）。

---

## ✅ 完了済み（前回レビューの反映）
- 承認APIの二重辞書問題は確認済み（前回レビューで妥当と判定された）。`GET /api/unregistered_units` 空 / `POST /api/register_unit` 404。
- SHA-256 hex直接保存は**撤回**。不正レコード（id=3, password=''）は削除済み。
- **正規登録完了**: RP1上で Werkzeug pbkdf2（scrypt:32768）ハッシュを生成 → 親機DBの `units` に INSERT。
  - 現在: `id=4, name='rp1', stock=10, initial_stock=10, connect=0→1, available=0, last_seen更新済み, ip_address=100.88.211.119`
  - 秘密の平文はチャット・コマンドライン・ログに一切出していない（RP1内生成 → scp経由でハッシュのみ転送 → 親機でファイルから読みINSERT → 一時ファイル削除済み）。

---

## 特に評価してほしい点
1. **親機の strict 評価矛盾**: `.env` は `OITERU_STRICT_SECURITY=false` なのに strict エラーが出る。考えられる原因は？
   - 例: (a) 環境変数が別経路で注入されている（tmux起動スクリプトの export? .env source? systemd?）、(b) `validate_runtime_security()` の strict 引数が DB 設定（`server_settings`）から来る、(c) .env の改行・BOM・エンコード問題、(d) 別の .env を読んでいる。
   - **確認に必要なコマンド**も提示してほしい。
2. **親機ダウンの原因調査**: どのログを見るべきか（journald? logs/ の何?）。OOM killer の可能性は？
3. **復旧手順**: 最小変更で親機を起動する最善手は？（例: `OITERU_STRICT_SECURITY=false` を明示的にexportして起動、DBの server_settings を確認、など）
4. **長期的な推奨**: 親機・子機を揃えて `53bc6ff` 相当に更新すべきか（前回レビューでは「セットで更新」推奨）。実機停止リスクを最小化する段取りは？
5. **RP1側の確認**: 親機復旧後の heartbeat 認証が 400/401 にならないか、`UNIT_SECRET_FILE` の読み込み経路（unit/configuration.py:23-50）で問題ないか。

## 返答形式
- 結論（3行以内）
- strict 矛盾の根本原因（コード引用つき）
- 復旧アクション（実行順、各1〜2行）
- ダウン原因の調査手順
- リスクと回避策
- 実機テスト再開前のチェックリスト
