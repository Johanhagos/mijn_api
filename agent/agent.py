"""Minimal AI Agent runner for mijn_api (Phase 1 scaffold).
This is a simple, safe starting point — no autonomous loops enabled by default.
"""
import sys
from .tools import run_script, deploy_vercel, check_api_health
from .memory import load_memory, save_memory


def run_agent(task: str):
    """Decide a simple action based on the task string and run a tool.
    This is intentionally minimal; extend with a planner and safety checks later.
    """
    task_l = task.lower()
    if "health" in task_l or "check" in task_l:
        return {"task": task, "result": check_api_health()}
    if "redeploy" in task_l or "deploy" in task_l:
        return {"task": task, "result": deploy_vercel()}
    if "run script" in task_l or task_l.startswith("run "):
        parts = task.split(maxsplit=1)
        script = parts[1] if len(parts) > 1 else None
        if script:
            return {"task": task, "result": run_script(script)}
    return {"task": task, "result": "no-op (unknown task)"}


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "Check site health"
    out = run_agent(task)
    print(out)
