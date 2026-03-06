# Security Notes

Urgent actions
- Rotate any credentials that were previously committed (One.com SFTP, other keys).

Environment variables
- Use the provided `.env.sample` and never commit a populated `.env`.
- Required vars used by One.com helpers: `ONE_SFTP_HOST`, `ONE_SFTP_USER`, `ONE_SFTP_PASSWORD`, `ONE_SFTP_PORT`, `ONE_SFTP_REMOTE_ROOT`, `ONE_LOCAL_UPLOAD_PATH`.

Quick secret-scan
- Install `gitleaks` and run:

  gitleaks detect --source . --report-path gitleaks-report.json

- Fallback grep (no gitleaks):

  git grep -n -I -E "password|passwd|secret|api[_-]?key|private_key|ssh-|BEGIN RSA PRIVATE KEY"

Removing secrets from history
- Rotate credentials immediately. If secrets are found in commit history, use `git-filter-repo` or the BFG Repo-Cleaner to purge them, then rotate again.

Prevention
- Add a pre-commit or CI secret-scan (gitleaks) to block commits with secrets.

CI / pre-commit
- A GitHub Actions workflow `/.github/workflows/secret-scan.yml` runs `gitleaks` on pushes and PRs and will fail checks if leaks are found.
- A `.pre-commit-config.yaml` using `detect-secrets` is included; install `pre-commit` locally and run `pre-commit install` to enable local checks.

Example local setup:

```bash
pip install pre-commit detect-secrets
pre-commit install
pre-commit run --all-files
```

Contact
- If you want, I can run the repo scan now and produce a findings report.
