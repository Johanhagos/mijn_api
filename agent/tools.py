"""Simple tool wrappers used by the agent.
These are intentionally small and synchronous. Add auth/safety before enabling destructive actions.
"""
import subprocess
import requests
import os


def run_script(script_name: str):
    """Run a local python script and return output."""
    try:
        p = subprocess.run(["python", script_name], capture_output=True, text=True, cwd=os.getcwd())
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode}
    except Exception as e:
        return {"error": str(e)}


def deploy_vercel():
    """Run `vercel --prod` if available. Ensure credentials set up locally first."""
    try:
        p = subprocess.run(["vercel", "--prod"], capture_output=True, text=True)
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode}
    except FileNotFoundError:
        return {"error": "vercel CLI not installed"}
    except Exception as e:
        return {"error": str(e)}


def check_api_health(url: str = "https://apiblockchain.io/health"):
    try:
        r = requests.get(url, timeout=10)
        return {"status_code": r.status_code, "body_sample": r.text[:1000]}
    except Exception as e:
        return {"error": str(e)}


def git_commit_and_push(message: str = "agent: automated commit"):
    """Basic git add/commit/push wrapper. Use with caution and proper safety checks."""
    try:
        subprocess.run(["git", "add", "-A"], check=False)
        c = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
        p = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        return {"commit_stdout": c.stdout, "commit_stderr": c.stderr, "push_stdout": p.stdout, "push_stderr": p.stderr}
    except Exception as e:
        return {"error": str(e)}


def read_logs(path: str, lines: int = 200):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read().splitlines()[-lines:]
        return "\n".join(data)
    except Exception as e:
        return {"error": str(e)}
