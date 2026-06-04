# 旧ランチャー資料について

この資料で扱っていた `launcher.sh`, `launcher.ps1`, `launcher.bat`, `launcher_gui.py`, `launcher_cui.py` は legacy 扱いです。

現在の標準手順は **Linux 系 OS + tmux + ローカル MySQL** です。新しく作業する人はランチャーではなく、次の手順を使ってください。

## 親機

```bash
cd ~/Desktop/oiteru_202603
cp .env.example .env
nano .env
scripts/setup_local_mysql.sh
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

## 子機

```bash
cd ~/Desktop/oiteru_202603
cp config.example.json config.json
nano config.json
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

## 詳細

| ファイル | 内容 |
|---|---|
| `../README.md` | 全体像 |
| `../docs/onboarding.md` | 新規参加者向け |
| `../取説書/QUICKSTART.md` | 詳細な起動手順 |
| `../docs/operations.md` | 運用・障害対応 |

最終更新: 2026-06-04
