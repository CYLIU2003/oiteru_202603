#!/usr/bin/env python3
"""WSL venv 依存パッケージ確認"""
import importlib

for mod in ["flask", "pandas", "requests", "numpy", "nfc", "openpyxl"]:
    try:
        m = importlib.import_module(mod)
        print(f"{mod}: OK", getattr(m, "__version__", ""))
    except Exception as e:
        print(f"{mod}: FAIL ({e})")
