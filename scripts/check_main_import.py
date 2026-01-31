#!/usr/bin/env python3
"""Helper: import `main` and print full traceback on failure.

Run this from the repo root inside the activated venv:

  python scripts/check_main_import.py

The script exits with code 1 and prints a Python traceback when import fails.
"""
import importlib
import traceback
import sys

try:
    importlib.import_module("main")
    print("Imported main successfully")
except Exception:
    traceback.print_exc()
    sys.exit(1)
