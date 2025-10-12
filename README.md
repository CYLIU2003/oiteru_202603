# OITELUシステム | REST APIサーバー & 子機クライアント

子機側のコードは Raspberry Pi 2 に配置されています。リポジトリを最新化したうえで、本書の手順に沿って親機・子機の環境を整えてから起動してください。

このプロジェクトは、Flask + SQLite による REST API サーバー（親機）と、NFC・モーター制御を行う Python スクリプト（子機）で構成されています。

2025 年 5 月の更新では、子機スクリプトが sudo 権限を自動で取得するようになり、親機の Web UI も一般利用者向けにデザインを刷新しました。詳細な変更内容は [CHANGELOG.md](CHANGELOG.md) を参照してください。

---

## ディレクトリ構成

```
oiteru_250827_restAPI/
├── app.py                  # Flask REST API サーバー本体（親機）
├── unit_client.py          # 子機クライアント（NFC・モーター制御）
├── requirements.txt        # 必要な Python パッケージ一覧
├── README.md               # このファイル
├── CHANGELOG.md            # 更新履歴
├── oiteru.sqlite3          # サーバー用データベース
├── userdb.sqlite3          # 旧ユーザーデータベース
├── static/
│   ├── css/
│   │   └── style20250506.css
│   └── img/
│       └── logo20250506.png
├── templates/              # Flask 用 HTML テンプレート
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── usage.html
│   ├── usage_result.html
│   ├── usage_error.html
│   ├── usage_status.html
│   ├── admin_login.html
│   ├── admin_dashboard.html
│   ├── admin_users.html
│   ├── admin_user_detail.html
│   ├── admin_units.html
│   ├── admin_unit_detail.html
│   ├── admin_new_unit.html
│   ├── admin_history.html
│   └── admin_restore.html
└── ...（その他のファイルやサンプルスケッチ等）
```

---

## 親機 (app.py)

### 主な機能

- 利用者情報（カード ID など）の管理
- 子機の接続状態や在庫数の管理
- Web ブラウザを通じた管理ダッシュボード
- データのバックアップと復元

### セットアップ手順

1. 必要なパッケージをインストール
    ```sh
    pip install -r requirements.txt
    ```
2. サーバーを起動
    ```sh
    python app.py
    ```

### 主な API エンドポイント

- `GET /api/users` : 全ユーザーの一覧を取得
- `GET /api/users/<card_id>` : 指定カード ID のユーザー情報を取得
- `POST /api/record_usage` : 利用を記録
- `POST /api/unit/heartbeat` : 子機からの生存確認

---

## 子機 (unit_client.py)

Raspberry Pi 上で動作し、NFC カードの読み取りとモーター制御を行うスクリプトです。

### 実行権限に関する注意

- Raspberry Pi などの Linux 環境では、GPIO や I2C を操作するために root 権限が必要です。
- `unit_client.py` は起動時に自動で権限を確認し、通常ユーザーで実行されている場合は `sudo` 経由で自分自身を再起動します。
- `sudo` コマンドが利用できない環境では、従来どおり手動で `sudo python unit_client.py` 等のコマンドを使用してください。
- 権限の昇格に失敗した場合は、ターミナルにエラーメッセージが表示されますので、指示に従って対処してください。

### 特徴

スクリプト冒頭の「かんたん設定」セクションを編集するだけで、以下の動作を簡単に切り替えられます。

- モーターの種類: サーボモーター / ステッピングモーター
- 制御方法: ラズパイ直結 (PCA9685) / Arduino 経由 (シリアル通信)
- センサーの有無: 排出検知センサーの利用 / 非利用
- GPIO ピン番号や Arduino ポート名も簡単に変更可能

### ハードウェア構成例

#### 構成1：Arduino 経由のステッピングモーター

1. Raspberry Pi と Arduino を USB ケーブルで接続
2. Arduino のピン (8, 9, 10, 11) を ULN2003 ドライバーの IN1〜IN4 に接続
3. Raspberry Pi の GPIO ピン (BCM 22) に排出検知センサーを接続
4. ULN2003 ドライバーにステッピングモーターと外部電源 (5V) を接続
5. 付属の .ino ファイルを Arduino に書き込み

#### 構成2：ラズパイ直結のサーボモーター

1. Raspberry Pi の I2C ピンを PCA9685 ドライバーに接続
2. PCA9685 ドライバーの任意のチャンネル（例: 15）にサーボモーターを接続
3. Raspberry Pi の GPIO ピン (BCM 22) に排出検知センサーを接続

### 注意事項

- `unit_client.py` を実行する前に、スクリプト上部の「かんたん設定」セクションで使用するハードウェア構成に合わせて設定を変更してください。
- NFC リーダーが未接続の場合、カード読み取り機能は動作しません。

---

## 親機 Web UI のリデザインについて

テンプレート (`templates/`) とスタイルシート (`static/css/style20250506.css`) を全面的に見直し、以下の改善を実施しています。

- ブランドカラーとロゴを活かしたヘッダーとヒーローセクション
- ステータスカードやボタンの視認性向上、およびレスポンシブ対応
- 読み取り状態のカラーコード化により、利用者が状況を直感的に把握可能
- 一般利用者でも迷わない導線と説明テキスト

デザインを調整する場合は `templates/base.html` を起点にテンプレートを編集し、共通スタイルは `static/css/style20250506.css` を更新してください。

---

## トラブルシューティング

- 親機サーバーが起動しない場合は、`requirements.txt` に記載された依存パッケージがインストールされているかを確認してください。
- 子機で sudo による再実行が繰り返される場合は、`sudo` コマンドが存在するか、または現在のユーザーが sudo 実行権限を持っているかを確認してください。
- NFC リーダーが認識されない場合は、配線と `config.json` の設定を再チェックしてください。

---

## ライセンス

本リポジトリのライセンスは別途指定がない限り社内利用を想定しています。外部公開する際は担当者に確認してください。
