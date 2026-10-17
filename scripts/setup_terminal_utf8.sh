#!/usr/bin/env bash
# 端末・tmux・ログの文字化けを防ぐため、このユーザーの環境を UTF-8 にそろえる。
#
#   scripts/setup_terminal_utf8.sh
#
# sudo は不要です。OS 全体の設定（/etc/default/locale）は変えず、
# 実行したユーザーの ~/.profile と ~/.bashrc に設定を追加します。何度実行しても同じ結果です。
# 反映するには、SSH を切ってつなぎ直してください（tmux の子機も起動し直します）。
set -euo pipefail

BEGIN="# >>> oiteru: UTF-8 >>>"
END="# <<< oiteru: UTF-8 <<<"
read -r -d '' BLOCK <<'SH' || true
# >>> oiteru: UTF-8 >>>
# OS の既定が EUC-JP などでも、端末とログを UTF-8 にそろえる（scripts/setup_terminal_utf8.sh が追加）
if locale -a 2>/dev/null | grep -qix 'ja_JP.utf8'; then
    export LANG=ja_JP.UTF-8 LC_ALL=ja_JP.UTF-8
else
    export LANG=C.UTF-8 LC_ALL=C.UTF-8
fi
unset LANGUAGE
export PYTHONUTF8=1
# <<< oiteru: UTF-8 <<<
SH

install_block() {
    local file="$1" tmp
    touch "$file"
    tmp="$(mktemp)"
    # 以前に追加したブロックを取り除いてから、先頭に入れ直す。
    # .bashrc は「対話でなければ終了」の行より前に置く必要があるため先頭にする。
    awk -v b="$BEGIN" -v e="$END" '$0==b{skip=1} !skip{print} $0==e{skip=0}' "$file" > "$tmp"
    { printf '%s\n' "$BLOCK"; cat "$tmp"; } > "$file"
    rm -f "$tmp"
    echo "更新しました: $file"
}

install_block "$HOME/.profile"
install_block "$HOME/.bashrc"

# git status などで日本語のファイル名を \343\202... と表示しない
git config --global core.quotepath false
echo "git の日本語ファイル名表示を有効にしました"

# shellcheck disable=SC1090
. <(printf '%s\n' "$BLOCK")
echo "これからの文字コード: $LANG"
echo "SSH をつなぎ直すと反映されます。"
