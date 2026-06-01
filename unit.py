#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=========================================
OITELU 子機 (NFC読み取り + モーター制御)
=========================================

main_stepping_branch では ULN2003AN + 28BYJ-48 のステッピングモーター運用を標準にします。
実装の詳細なブランチ専用差分は stepping_patch.py に分離しています。
"""

import os
import sys

from stepping_patch import patch_unit_client_source


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    unit_client_path = os.path.join(script_dir, 'archive', 'unit_client.py')
    if not os.path.exists(unit_client_path):
        print(f"エラー: {unit_client_path} が見つかりません")
        sys.exit(1)

    with open(unit_client_path, 'r', encoding='utf-8') as f:
        source = f.read()

    patched_source = patch_unit_client_source(source)
    exec_globals = {
        '__name__': '__main__',
        '__file__': unit_client_path,
        '__package__': None,
    }
    exec(compile(patched_source, unit_client_path, 'exec'), exec_globals)


if __name__ == '__main__':
    main()
