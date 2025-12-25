# 📖 OITERU（オイテル）システム 取扱説明書（詳細）

<div style="text-align: center; margin-bottom: 20px;">
    <span class="badge badge-primary">Version 2.0</span>
    <span class="badge badge-accent">Updated: 2025-12-24</span>
</div>

このドキュメントは **OITERUシステム（NFCカードでお菓子等を管理・排出するIoTシステム）** の全体仕様・機能・設定・運用方法を、初めて触る方にも分かるようにまとめた「取扱説明書」です。

<div class="alert alert-info">
    <strong>ナビゲーション:</strong>
    <ul>
        <li>🔰 <strong>まず動かす</strong>: <a href="QUICKSTART.html">取説書/QUICKSTART.html</a> (または .md)</li>
        <li>📖 <strong>仕様を理解する</strong>: このドキュメント</li>
    </ul>
</div>

---

## 1. 🏗️ システムの全体像

OITERUは大きく次の3要素で構成されます。

1.  **親機（サーバー）**: Web管理画面とAPIを提供し、利用履歴・在庫・ユーザーを管理します。
2.  **従親機（サーバー）**: 親機と同じWeb/APIを動かしつつ、**DBは持たず外部DB（MySQL）を参照**して動作します（複数サーバー運用用）。
3.  **子機（Raspberry Pi など）**: NFCを読み取り、必要に応じてモーターを動かし、サーバーに利用を通知します。

### 1.1 役割分担（超要約）

| 役割 | 説明 |
| :--- | :--- |
| **親機/従親機** | 「誰が」「いつ」「何回」使ったか、子機の接続状況、在庫などを管理。 |
| **子機** | 現場のNFC読み取り・排出（モーター制御）・状態送信。 |

---

## 2. 📂 リポジトリ（主要ファイル）

<div class="alert alert-secondary">
    <strong>主要コンポーネント:</strong>
    <ul>
        <li><code>server.py</code> … 親機 / 従親機（Flask Webサーバー本体）</li>
        <li><code>db_adapter.py</code> … DB抽象化（SQLite / MySQLを切替）</li>
        <li><code>unit.py</code> … 子機クライアント（NFC・モーター・センサー）</li>
        <li><code>config.json</code> … 子機の設定（接続先URL、ユニット名、モーター方式等）</li>
    </ul>
</div>

**補助ディレクトリ:**
- `templates/` … 管理画面HTML
- `static/` … CSS/画像
- `tools/` … 診断・テスト用スクリプト
- `scripts/` … 起動/セットアップ用スクリプト
- `docker/` … Docker構成

---

## 3. 🖥️ 親機/従親機（`server.py`）の仕様

`server.py` は同一コードで **親機** と **従親機** の両方として動けます。

- **SQLiteを使う**: ローカルに `oiteru.sqlite3` を作成して運用（開発/単体運用向け）
- **MySQLを使う**: 外部MySQLに接続して運用（複数サーバー/本番構成向け）

### 3.1 DB切替（重要）

DBの種類は主に環境変数で決まります。

<div class="alert alert-warning">
    <strong>設定方法:</strong>
    <ul>
        <li><code>DB_TYPE=mysql</code> … MySQLへ接続</li>
        <li><code>DB_TYPE=sqlite</code>（または未指定）… ローカルSQLite（<code>oiteru.sqlite3</code>）</li>
    </ul>
</div>

※ 実際の接続先情報（ホスト・ユーザー等）は `server.py` / `db_adapter.py` 側の実装と、Docker環境変数（`docker-compose.*.yml`）の指定に従います。

### 3.2 サーバー設定（環境変数）

`server.py` では以下の環境変数が利用されます。

| 変数名 | 説明 | デフォルト値 |
| :--- | :--- | :--- |
| `SERVER_NAME` | 管理画面等に表示するサーバー名 | `OITERU親機` |
| `SERVER_LOCATION` | 設置場所 | `未設定` |

**グローバル設定（初期値は環境変数、以降DBから同期）:**
- `AUTO_REGISTER_MODE` … 未登録カードを自動登録するか（`true/false`）
- `AUTO_REGISTER_STOCK` … 自動登録ユーザーの初期在庫
- `DAILY_LIMIT` … 1日あたりの取得上限

### 3.3 設定同期（settingsテーブル）

`server.py` は `settings` テーブルを使って、サーバー設定をDBに保存/読み込みします。
複数従親機が同一DBを見る場合、設定をDBに集約すると同じ設定を共有できます。

### 3.4 データベース初期化

- **SQLite運用**: `server.py` の `init_db()` が `oiteru.sqlite3` が無い場合にテーブルを作成します。
- **MySQL運用**: 基本は `docker/init_mysql.sql` で初期化します。

---

## 4. 📡 子機（`unit.py`）の仕様

子機は概念的に次の仕事をします。

1.  NFCカードを読み取る
2.  サーバーへ照会/利用記録を送る（ユーザーの在庫や制限を反映）
3.  利用OKならモーターを動かして排出
4.  必要に応じてセンサーで排出完了を検知
5.  状態（生存/診断/ログ）をサーバーへ送る

---

## 5. ⚙️ 子機設定ファイル（`config.json`）

`config.json` は子機の動作を決める重要ファイルです。

<div class="alert alert-danger">
    <strong>必須設定:</strong>
    <ul>
        <li><code>SERVER_URL</code> … 親機/従親機のURL（例: <code>http://192.168.1.10:5000</code>）</li>
        <li><code>UNIT_NAME</code> … 子機名（サーバー側の <code>units</code> と紐づく）</li>
        <li><code>UNIT_PASSWORD</code> … 子機認証用パスワード</li>
    </ul>
</div>

**モーター/制御:**
- `MOTOR_TYPE` … `SERVO` / （他方式があれば `unit.py` に準拠）
- `CONTROL_METHOD` … `RASPI_DIRECT` / `ARDUINO` 等
- `MOTOR_SPEED` … 回転速度
- `MOTOR_DURATION` … 動作時間（秒）

**センサー/LED:**
- `USE_SENSOR` … 排出検知センサーを使う
- `SENSOR_PIN` … GPIOピン
- `GREEN_LED_PIN` / `RED_LED_PIN` … LED GPIOピン

---

## 6. 📊 管理画面（Web UI）

`templates/` 配下に管理画面があり、`server.py` がレンダリングします。

- 🔐 管理者ログイン
- 👥 ユーザー一覧・詳細
- 🤖 子機一覧・詳細
- 📜 履歴（利用/エラー）
- 🩺 診断情報（子機からの情報を表示）
- ⚙️ 設定変更（自動登録モード、日次制限など）

---

## 7. 📈 運用の考え方（例）

### 7.1 小規模（検証/教室/研究室）
- **構成**: 親機1台（SQLite） + 子機数台
- **メリット**: 構築が簡単
- **注意**: DBファイルのバックアップ（`oiteru.sqlite3`）を定期的に行う

### 7.2 中〜大規模（複数拠点/冗長化）
- **構成**: 親機/従親機複数（同一MySQL） + 子機複数
- **メリット**: サーバー増設が容易
- **注意**: MySQLの運用（バックアップ、ユーザー権限、ポート開放）

---

## 8. 🛠️ ログ・診断・トラブル対応の基本

### 8.1 まず確認すること（共通）
1.  サーバーが起動しているか（5000番がLISTENしているか）
2.  `SERVER_URL` が正しいか（子機→サーバーへ到達できるか）
3.  DB接続情報が正しいか（MySQLの場合）
4.  子機名/パスワードが一致しているか

### 8.2 ありがちな原因
- **ポート競合（5000）**: 別プロセスが使用
- **Firewall**: Windowsファイアウォールが遮断
- **DB未初期化**: MySQLでテーブルが無い/権限が無い
- **config.jsonのSERVER_URL間違い**: IP変更・http/https違い
- **NFCデバイス未認識**: USB接続・権限・デバイスパス違い

---

## 9. 🔒 セキュリティ注意

<div class="alert alert-danger">
    <strong>セキュリティチェックリスト:</strong>
    <ul>
        <li>管理者パスワードが初期のままになっていないか</li>
        <li>子機パスワード（<code>UNIT_PASSWORD</code>）が弱すぎないか</li>
        <li>外部に5000番（Flask）やMySQLを公開する場合はアクセス制御（FW/VPN）を前提にする</li>
    </ul>
</div>

---

## 10. 📚 関連ドキュメント

- <a href="QUICKSTART.html">取説書/QUICKSTART.html</a> … 起動手順とトラブルシューティング
- `docker/` … Docker構成
- `scripts/` … 便利スクリプト
