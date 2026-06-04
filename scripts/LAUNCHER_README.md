# 旧ランチャー README

このファイルで以前説明していた GUI/CUI ランチャーは legacy 扱いです。

現在の標準運用は **Linux 系 OS + tmux + ローカル MySQL** です。ランチャーの複数モードや Docker 経路は、当面の開発・学内実証では使わないでください。

## 現行の推奨起動

親機:

```bash
cd ~/Desktop/oiteru_202603
cp .env.example .env
nano .env
scripts/setup_local_mysql.sh
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

子機:

```bash
cd ~/Desktop/oiteru_202603
cp config.example.json config.json
nano config.json
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

状態確認:

```bash
scripts/tmux_oiteru.sh status
tmux ls
systemctl status mysql
```

## legacy ファイル

| ファイル | 扱い |
|---|---|
| `launcher.sh` | legacy |
| `launcher.ps1` | legacy |
| `launcher.bat` | legacy |
| `launcher_gui.py` | legacy |
| `launcher_cui.py` | legacy |
| `launcher_utils.py` | legacy ランチャー用 |
| `launcher_config.json` | legacy ランチャー用 |

## 詳細

| ファイル | 内容 |
|---|---|
| `../README.md` | 全体像 |
| `../docs/onboarding.md` | 新規参加者向け |
| `../取説書/QUICKSTART.md` | 詳細な起動手順 |
| `../docs/operations.md` | 運用・障害対応 |
| `README.md` | scripts ディレクトリの現行説明 |

最終更新: 2026-06-04
