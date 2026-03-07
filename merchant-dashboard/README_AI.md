## Enabling OpenAI / ChatGPT for the Merchant Dashboard

This document explains how to securely add your OpenAI API key so the dashboard AI (`/ai/chat`) uses ChatGPT models.

1) Choose where the backend runs
- Local dev: your machine (you will set an env var locally)
- Hosted: Vercel, GitHub Actions, Railway, or your server (use the platform's secret store)

2) Add the OpenAI key (do NOT commit keys)
- Vercel (recommended for hosting frontend + backend env):
  - Project → Settings → Environment Variables
  - Add `OPENAI_API_KEY` (set for `Preview` and `Production` as needed)
  - Optionally add `OPENAI_MODEL` (e.g., `gpt-4o`) and `OPENAI_TEMPERATURE`

- GitHub Actions / CI:
  - Repository → Settings → Secrets and variables → Actions → New repository secret
  - Name: `OPENAI_API_KEY`
  - (Optional) `OPENAI_MODEL`, `OPENAI_TEMPERATURE`
  - Use these secrets in your CI or deployment workflow; the backend reads them at runtime.

- Local (PowerShell example):
  ```powershell
  $env:OPENAI_API_KEY = "<NEW_KEY>"
  python run_uvicorn_8002.py
  ```
  Or persist for your user:
  ```powershell
  [System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY","<NEW_KEY>","User")
  ```

3) Select ChatGPT model
- The backend uses `OPENAI_MODEL` (defaults to `gpt-3.5-turbo` unless overridden). Set `OPENAI_MODEL=gpt-4o` (or another model you have access to) in your environment.

4) Restart backend / redeploy
- After adding secrets restart the backend (or trigger a redeploy) so the new env vars are picked up.

5) Test the integration
- Example PowerShell test (local backend):
  ```powershell
  Invoke-RestMethod -Uri 'http://127.0.0.1:8002/ai/chat' -Method POST -ContentType 'application/json' -Body '{"message":"Explain VAT for NL B2C","context":{"merchant":{"name":"Test","country":"NL"},"stats":{}}}' | ConvertTo-Json -Depth 5
  ```

6) Security notes
- Never commit `OPENAI_API_KEY` or other secrets to the repo.
- Revoke any exposed keys immediately and replace them.
- Use platform secret stores (Vercel/GitHub) for production and CI.
