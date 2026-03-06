AI Agent for mijn_api

Purpose
- Minimal scaffold for an autonomous DevOps agent that can run repo scripts, check API health, and deploy to Vercel.

How to run (manual):
- Install dependencies (requests)

    pip install -r agent/requirements.txt

- Run a simple task:

    python -m agent.agent "Check site health"

Next steps
- Iterate Phase 1: define agent responsibilities and safety rules.
- Add credentials to a secure vault before enabling deploy/commit tools.
