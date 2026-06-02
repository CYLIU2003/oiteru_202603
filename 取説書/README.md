# OITERU 取説書

このフォルダは、OITERU を初めて触る人が迷わず作業できるようにするための説明書置き場です。

標準の作業環境は **Linux 系 OS + tmux** です。Windows や GUI ランチャーの説明は補足扱いにし、日常運用では Linux/tmux の手順を優先してください。

## このフォルダの読み方

| 目的 | 読むファイル |
|---|---|
| まず起動したい | `QUICKSTART.md` |
| スマホやブラウザで概要を見たい | `QUICKSTART.html` |
| 過去の変更履歴を見たい | `CHANGELOG_2026-01-23.md` |
| 日常運用・障害対応を見たい | `../docs/operations.md` |

## 初心者向け最短ルート

1. `../README.md` を読む
2. `QUICKSTART.md` の「共通準備」を行う
3. 親機を `tmux` で起動する
4. 子機を `tmux` で起動する
5. 管理画面にログインする
6. 子機 CUI でモーターの正方向・逆方向テストを行う
7. NFC カードをかざして排出動作を確認する

## 用語

| 用語 | 意味 |
|---|---|
| 親機 | 管理画面と DB を持つメインサーバー |
| 子機 | Raspberry Pi などで NFC 読み取りと排出を行う端末 |
| 従親機 | 親機 DB を参照する追加サーバー。必要な場合だけ使う |
| tmux | SSH を切っても起動中の画面を残せるターミナル管理ツール |
| venv | Python の仮想環境。依存パッケージを安全に分ける仕組み |
| MySQL | 標準 DB。SQLite は legacy 扱い |
| heartbeat | 子機が親機へ定期的に状態を送る通信 |

## 標準運用

| 項目 | 標準 |
|---|---|
| 親機起動 | `tmux new -s oiteru-parent` → `./venv-start.sh parent-mysql` |
| 子機起動 | `tmux new -s oiteru-unit` → `./venv-start.sh unit` |
| DB | MySQL 8 (InnoDB) |
| MySQL 起動 | `docker compose -f docker-compose.mysql.yml up -d` |
| 管理画面 | `http://<親機IP>:5000/admin` |
| 子機モーター | 28BYJ-48 + ULN2003AN |
| モーターバックエンド | PigpioZero → RpiMotorLib → GPIO fallback |

## ファイル構成

```text
取説書/
├── README.md                 # このファイル。読む順番と全体像
├── QUICKSTART.md             # 親機・子機を Linux/tmux で起動する手順
├── QUICKSTART.html           # ブラウザ向けの簡易案内
├── CHANGELOG_2026-01-23.md   # 過去の変更履歴
└── manual.css                # HTML 表示用 CSS
```

## 作業前チェックリスト

| チェック | コマンドまたは確認内容 |
|---|---|
| リポジトリにいる | `pwd` |
| ブランチ確認 | `git branch --show-current` |
| 最新化 | `git pull` |
| 親機設定がある | `.env` が存在する |
| 子機設定がある | `config.json` が存在する |
| tmux がある | `tmux -V` |
| MySQL が起動している | `docker compose -f docker-compose.mysql.yml ps` |
| 子機 pigpio が起動している | `systemctl status pigpiod` |

## 困ったときの入口

| 症状 | まず見る場所 |
|---|---|
| 起動方法が分からない | `QUICKSTART.md` |
| tmux から戻れない | `QUICKSTART.md` の tmux 章 |
| 管理画面に入れない | `../docs/operations.md` |
| 子機がオンラインにならない | `QUICKSTART.md` のトラブルシューティング |
| モーターが回らない | `QUICKSTART.md` の子機モーター確認 |
| NFC が読めない | `QUICKSTART.md` のトラブルシューティング |
| DB 接続に失敗する | `../docs/operations.md` |

## 注意事項

`.env`, `config.json`, ログ、実 DB、パスワード、カード UID は Git に含めないでください。

古い資料に `server.py`, SQLite, Windows PowerShell, `oiteru_250827_restAPI` のような記述が残っている場合があります。現在の標準は `oiteru_202603`, Linux/tmux, MySQL, `db_server.py`, `unit.py` です。

最終更新: 2026-06-02
