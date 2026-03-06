# History cleanup (remove leaked secrets)

Important: rotate any exposed credentials (One.com SFTP, API keys) before rewriting git history.

High-level safe flow
1. Rotate credentials out-of-band (change the password on One.com now).
2. Push rotated values to your deployment environments as needed.
3. Create a backup branch and push it: `git branch backup-before-secret-clean; git push origin backup-before-secret-clean`.
4. Run the cleanup script below (requires `git-filter-repo` installed locally).
5. Inspect the repository, then force-push rewritten history: `git push --force --all && git push --force --tags`.
6. Inform collaborators to re-clone (history rewritten).

Tools
- Preferred: `git-filter-repo` (fast, recommended). Install: `pip install git-filter-repo` or follow https://github.com/newren/git-filter-repo
- Alternative: BFG Repo-Cleaner (Java-based).

Replacement file
The included scripts create a `replacements.txt` mapping discovered secrets to `[REDACTED]`.

Risks & notes
- Rewriting history is destructive: it changes commit SHAs and requires force-push and coordination.
- After force-push, all collaborators must clone again; open PRs will be affected.

If you want me to run the cleanup here, confirm you've rotated credentials and that it's OK to force-push to `origin/main`.
