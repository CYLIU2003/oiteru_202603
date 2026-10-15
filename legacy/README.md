# legacy/

使わなくなったファイルの置き場です。**標準の手順では使いません。はじめての人は読まなくて大丈夫です。**

ここにあるものは、今の構成（親機は Linux + MySQL + systemd、子機は Raspberry Pi）では動かないか、
別の方法に置き換わっています。昔の手順を調べるときだけ参照してください。

| 場所 | 中身 | 今の代わり |
|---|---|---|
| `docker/`, `docker-start.sh`, `docker-compose.mysql.yml`, `.dockerignore` | Docker で親機・子機を動かす構成 | `scripts/parent.sh`（systemd） |
| `scripts/launcher*`, `scripts/quick_start_*`, `scripts/start_*` | 古い起動スクリプト（Docker 前提・古いパスを含む） | `scripts/parent.sh`, `scripts/tmux_oiteru.sh` |
| `scripts/*card_reader*`, `scripts/test_nfc_in_container.sh` | WSL / Docker 用のカードリーダー接続 | `scripts/init_card_reader.sh`, `tools/check_nfc_reader.py` |
| `scripts/*mysql_port*`, `scripts/setup_multi_server.sh` | 複数サーバー構成用 | 単独の親機構成 |
| `tools/` | SQLite 時代の確認スクリプト、WSL 用の一時検証 | `tools/check_nfc_reader.py` |
| `app.py`, `data_viewer.py`, `old_scripts/` | SQLite 版の親機とデータビューアー | `server.py` + MySQL |

ファイルを復活させるときは、`git mv legacy/<ファイル> <元の場所>` で戻せます。
