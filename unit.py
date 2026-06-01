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

from stepping_patch import STEPPER_DIRECT_BRANCH, patch_unit_client_source


STEPPER_BRANCH_MARKER = "elif current_motor_type == 'STEPPER' and current_control_method == 'RASPI_DIRECT':"
ARDUINO_BRANCH_MARKER = "        elif current_control_method == 'ARDUINO_SERIAL':"


def ensure_stepper_dispense_branch(source: str) -> str:
    """dispense_item() に STEPPER/RASPI_DIRECT 分岐が必ず入っている状態にする。

    以前のパッチでは診断文中の "STEPPER/RASPI_DIRECT" 文字列を検出してしまい、
    実際の elif 分岐注入をスキップする可能性があった。ここでは elif 文そのものを
    マーカーにして、存在しなければ Arduino 分岐の直前へ強制挿入する。
    """
    if STEPPER_BRANCH_MARKER in source:
        print("[stepping_patch] STEPPER/RASPI_DIRECT dispense branch: OK")
        return source

    if ARDUINO_BRANCH_MARKER not in source:
        raise RuntimeError("Arduino分岐が見つからず、STEPPER/RASPI_DIRECT 分岐を挿入できません")

    print("[stepping_patch] STEPPER/RASPI_DIRECT dispense branch: injected")
    return source.replace(ARDUINO_BRANCH_MARKER, STEPPER_DIRECT_BRANCH + "\n" + ARDUINO_BRANCH_MARKER, 1)


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
    patched_source = ensure_stepper_dispense_branch(patched_source)

    exec_globals = {
        '__name__': '__main__',
        '__file__': unit_client_path,
        '__package__': None,
    }
    exec(compile(patched_source, unit_client_path, 'exec'), exec_globals)


if __name__ == '__main__':
    main()
