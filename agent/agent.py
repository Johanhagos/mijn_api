"""Minimal AI Agent runner for mijn_api (Phase 1 scaffold).
This is a simple, safe starting point — no autonomous loops enabled by default.
"""
import sys
from .tools import run_script, deploy_vercel, check_api_health
from .memory import load_memory, save_memory
from .ai_integration import format_vat_summary
from .country_map import lookup as lookup_country


def run_agent(task: str):
    """Decide a simple action based on the task string and run a tool.
    This is intentionally minimal; extend with a planner and safety checks later.
    """
    task_l = task.lower()
    if "health" in task_l or "check" in task_l:
        return {"task": task, "result": check_api_health()}
    # VAT lookup support: e.g. "vat sweden" or "what is the vat of se"
    if "vat" in task_l:
        # try to extract country code or name
        parts = task.split()
        # look for a 2-letter code in the task
        code = None
        for p in parts:
            if len(p) == 2 and p.isalpha():
                code = p.upper()
                break
        # fallback: attempt to resolve a country name
        if not code and len(parts) > 1:
            # try join of last words as a name
            name_try = " ".join(parts[1:]).strip()
            code = lookup_country(name_try)
        # final fallback: last token first two letters
        if not code and len(parts) > 0:
            code = parts[-1][:2].upper()
        if code:
            summary = format_vat_summary(code)
            return {"task": task, "result": summary}
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
