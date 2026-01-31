#!/usr/bin/env python3
"""Helper: import `main` and print full traceback on failure.

Run this from the repo root inside the activated venv:

  python scripts/check_main_import_fixed.py

The script exits with code 1 and prints a Python traceback when import fails.
"""
import importlib
import traceback
import sys
from pathlib import Path

# Ensure project root (one level up from scripts/) is on sys.path so `import main`
# resolves when this script is executed directly (sys.path[0] is the script dir).
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    importlib.import_module("main")
    print("Imported main successfully")
except Exception:
    traceback.print_exc()
    sys.exit(1)
