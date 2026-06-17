#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OITERU unit launcher.

The actual unit client lives in archive/unit_client.py for now.  Keep this
file small so both servo and stepper branches can share the same entry point:
`python unit.py`.
"""

import os
import runpy
import sys


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    unit_client_path = os.path.join(script_dir, 'archive', 'unit_client.py')
    if not os.path.exists(unit_client_path):
        print(f"エラー: {unit_client_path} が見つかりません")
        sys.exit(1)

    runpy.run_path(unit_client_path, run_name='__main__')


if __name__ == '__main__':
    main()
