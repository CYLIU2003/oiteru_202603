# OITERU 開発オンボーディング

この文書は、新しく OITERU 開発に参加する人が、どこから読んで、何を壊さないように作業すればよいかをまとめた入口です。

## 参加したら最初にやること

1. `README.md` で全体像を読む
2. `取説書/QUICKSTART.md` で tmux 起動を一度なぞる
3. `.env.example` と `config.example.json` を見て、秘密情報を Git に入れない感覚をつかむ
4. `docs/operations.md` で障害時に見る場所を知る
5. 小さい修正から始める

## 標準の開発環境

| 項目 | 標準 |
|---|---|
| OS | Linux 系 OS |
| 起動 | tmux |
| DB | ローカル MySQL 8 |
| 親機 | `db_server.py` |
| 子機 | `unit.py` |
| Python 仮想環境 | `.venv` |

Docker は当面の標準手順では使いません。古い資料やスクリプトに Docker の記述があっても、初回セットアップでは `scripts/setup_local_mysql.sh` と `scripts/tmux_oiteru.sh` を優先してください。

## 公式ダウンロード URL

| ソフトウェア | 用途 | URL |
|---|---|---|
| Ubuntu | 親機 Linux OS の候補 | https://ubuntu.com/download |
| Raspberry Pi Imager | Raspberry Pi OS を SD カードへ書き込む | https://www.raspberrypi.com/software/ |
| Raspberry Pi OS | 子機 OS | https://www.raspberrypi.com/software/operating-systems/ |
| Python | Python 本体 | https://www.python.org/downloads/ |
| Git | Git CLI | https://git-scm.com/downloads |
| MySQL Community Server | 親機 DB | https://dev.mysql.com/downloads/mysql/ |
| tmux | tmux 本体。Linux では通常 `apt` で入れる | https://github.com/tmux/tmux/releases |
| Visual Studio Code | 推奨エディタ | https://code.visualstudio.com/download |
| Tailscale | 別ネットワーク間で使う任意 VPN | https://tailscale.com/downloads |

## 初回セットアップ

```bash
cd ~/Desktop/oiteru_202603
git pull

sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip mysql-server curl

cp .env.example .env
nano .env

scripts/setup_local_mysql.sh
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

子機を触る場合:

```bash
cp config.example.json config.json
nano config.json

scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

## 作業前チェック

```bash
git branch --show-current
git pull
git status --short
tmux ls
systemctl status mysql
```

作業ツリーに自分が触っていない変更がある場合は、勝手に戻さないでください。誰かの作業かもしれません。

## 触る場所の目安

| やりたいこと | 主な場所 |
|---|---|
| 管理画面 API | `db_server.py`, `server.py`, `templates/` |
| DB 接続 | `db_adapter.py`, `.env.example` |
| 子機通信 | `archive/unit_client.py` |
| 子機起動 | `unit.py` |
| ハード制御 | `stepper_driver.py`, `archive/unit_client.py` の `dispense_item()` |
| 起動手順 | `scripts/`, `README.md`, `取説書/QUICKSTART.md` |
| 運用資料 | `docs/operations.md` |

今後の整理では、HTTP ルーティング、業務ロジック、DB アクセス、認証、ハード制御を分けていく方針です。新しいコードを足すときは、route handler に SQL や GPIO 処理を直接増やさないようにしてください。

子機のモーター制御は、まず `archive/unit_client.py` の `dispense_item()` を入口として読みます。ステッピングモーターの GPIO 詳細は `stepper_driver.py` に集約しているため、`unit.py` へ分岐やパッチ処理を増やさないでください。

## やってはいけないこと

| 禁止 | 理由 |
|---|---|
| `.env` や `config.json` をコミットする | パスワードや設置情報が入る |
| 平文パスワードをコードに書く | 実証運用で漏えいリスクになる |
| `print()` だけで運用ログを増やす | 障害時に追いにくい |
| route handler に直接 SQL を増やす | 責務分離しにくくなる |
| 実機 GPIO/NFC 処理を業務ロジックへ直書きする | モックテストできない |
| SQLite 前提の新規実装を増やす | 標準 DB は MySQL |

## 小さい PR の例

| よい粒度 | 内容 |
|---|---|
| README 修正だけ | 起動手順の改善 |
| 起動スクリプトだけ | tmux 起動の補助 |
| 認証修正だけ | パスワード・セッション周り |
| API 異常系だけ | エラー形式や入力検証 |
| DB repository だけ | SQL を閉じ込める整理 |

認証変更、DB 全変更、UI 大改修を同時に入れる巨大 PR は避けてください。

## 動作確認

```bash
python -m unittest
scripts/tmux_oiteru.sh status
curl http://localhost:5000
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
```

実機が必要な確認は、作業メモに「実機未確認」または「実機確認済み」と残してください。

## 困ったとき

| 症状 | 見る場所 |
|---|---|
| 起動できない | `取説書/QUICKSTART.md` |
| tmux に戻れない | `scripts/tmux_oiteru.sh status` |
| 管理画面に入れない | `docs/operations.md` |
| DB 接続に失敗する | `.env`, `systemctl status mysql` |
| 子機がオンラインにならない | `config.json`, 子機 tmux ログ |

最終更新: 2026-06-17
