#!/usr/bin/env python3
"""Strip Markdown-style fenced code blocks wrapping source files.

Some files in `merchant-dashboard` were accidentally saved with leading and trailing
code fences like ```tsx or ```typescript. This script removes those fences in-place
for common source file extensions.

Usage:
  python scripts/strip_code_fences.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_DIR = ROOT / "merchant-dashboard"
EXTS = {'.ts', '.tsx', '.js', '.jsx', '.d.ts'}

fence_re = re.compile(r'^```\w*\s*$')

def fix_file(p: pathlib.Path) -> bool:
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        return False

    lines = text.splitlines()
    if not lines:
        return False

    changed = False
    # Remove leading fence
    if fence_re.match(lines[0]):
        lines = lines[1:]
        changed = True

    # Remove trailing fence if present
    if lines and fence_re.match(lines[-1]):
        lines = lines[:-1]
        changed = True

    if changed:
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return changed

def main():
    changed_files = []
    for p in TARGET_DIR.rglob('*'):
        if p.is_file() and p.suffix in EXTS:
            if fix_file(p):
                changed_files.append(str(p.relative_to(ROOT)))

    if changed_files:
        print('Fixed fences in:')
        for f in changed_files:
            print(' -', f)
    else:
        print('No fenced files found.')

if __name__ == '__main__':
    main()
