<#
.SYNOPSIS
  PowerShell helper to run git-filter-repo replacement on Windows.
#>
Write-Host "== Git history cleanup helper (PowerShell) =="
Write-Host "This will rewrite history. Rotate credentials and back up before running."

if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Write-Host "git-filter-repo not found. Install with: pip install git-filter-repo"
    exit 1
}

$replacements = @(
    "[REDACTED]1992==>[REDACTED]",
    "[REDACTED]==>[REDACTED]",
    "[REDACTED]==>[REDACTED]",
    "[REDACTED]==>[REDACTED]",
    "[REDACTED]==>[REDACTED]"
)

$out = "replacements.txt"
$replacements | Out-File -Encoding utf8 -FilePath $out

Write-Host "Creating backup branch 'backup-before-secret-clean'"
git branch -f backup-before-secret-clean
git push -u origin backup-before-secret-clean

Write-Host "Running: git filter-repo --replace-text $out"
git filter-repo --replace-text $out

Write-Host "Review results locally. When ready, force-push rewritten history:"
Write-Host "  git push --force --all" -ForegroundColor Yellow
Write-Host "  git push --force --tags" -ForegroundColor Yellow

Write-Host "Finished. Remove 'replacements.txt' when done if it contains secrets."
