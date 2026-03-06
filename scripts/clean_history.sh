#!/usr/bin/env bash
set -euo pipefail

echo "== Git history cleanup helper =="
echo "This will rewrite history. DO NOT run until you have rotated exposed credentials and backed up the repo."

if ! command -v git-filter-repo >/dev/null 2>&1; then
  echo "git-filter-repo not found. Install with: pip install git-filter-repo"
  exit 1
fi

cat > replacements.txt <<'EOF'
[REDACTED]1992==>[REDACTED]
[REDACTED]==>[REDACTED]
[REDACTED]==>[REDACTED]
[REDACTED]==>[REDACTED]
[REDACTED]==>[REDACTED]
EOF

echo "Creating backup branch 'backup-before-secret-clean'"
git branch -f backup-before-secret-clean
git push -u origin backup-before-secret-clean

echo "Running git-filter-repo --replace-text replacements.txt"
git filter-repo --replace-text replacements.txt

echo "Review results locally. To publish rewritten history run (when ready):"
echo "  git push --force --all"
echo "  git push --force --tags"

echo "Cleanup helper finished. Remove 'replacements.txt' when done if it contains secrets."
