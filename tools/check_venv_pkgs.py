"""Ubuntu 26.04 venv の主要パッケージを確認するスクリプト (WSL 内で実行)"""
import importlib.metadata as md

PACKAGES = ["nfc", "flask", "pandas", "PyMySQL", "gunicorn", "numpy", "openpyxl", "requests"]

for pkg in PACKAGES:
    try:
        ver = md.version(pkg)
        print(f"OK   {pkg}=={ver}")
    except md.PackageNotFoundError:
        print(f"MISS {pkg}")

# nfcpy の import テスト
try:
    import nfc

    print("NFC_IMPORT_OK", nfc.__version__)
except Exception as exc:  # noqa: BLE001
    print("NFC_IMPORT_FAIL", exc)
