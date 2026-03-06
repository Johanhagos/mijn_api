"""FastAPI router for the agent.
Safe defaults: agent disabled by env var `AGENT_ENABLED` (must be "1").
Extra safety: destructive actions like deploy or git push require `AGENT_ALLOW_DEPLOY=1`.

Mount with::

    from fastapi import FastAPI
    from agent.router import router as agent_router

    app = FastAPI()
    app.include_router(agent_router, prefix="/agent")

"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os
from .agent import run_agent
from .memory import load_memory, save_memory

router = APIRouter()

AGENT_ENABLED = os.environ.get("AGENT_ENABLED", "0") == "1"
AGENT_ALLOW_DEPLOY = os.environ.get("AGENT_ALLOW_DEPLOY", "0") == "1"


class AgentTask(BaseModel):
    task: str


@router.post("/run")
async def run_task(body: AgentTask, request: Request):
    if not AGENT_ENABLED:
        raise HTTPException(status_code=403, detail="Agent API is disabled (set AGENT_ENABLED=1 to enable)")

    task = body.task.strip()
    # safety: block deploy/git unless explicitly allowed
    low = task.lower()
    if ("deploy" in low or "push" in low or "git" in low) and not AGENT_ALLOW_DEPLOY:
        return {"status": "blocked", "reason": "Destructive actions disabled. Set AGENT_ALLOW_DEPLOY=1 to allow."}

    result = run_agent(task)
    # record in memory
    mem = load_memory()
    history = mem.get("history", [])
    entry = {"task": task, "result": result}
    history.append(entry)
    mem["history"] = history[-200:]
    save_memory(mem)
    return {"status": "ok", "result": result}


@router.get("/status")
async def status():
    mem = load_memory()
    return {"agent_enabled": AGENT_ENABLED, "allow_deploy": AGENT_ALLOW_DEPLOY, "memory_summary": {"entries": len(mem.get("history", []))}}


@router.get("/memory")
async def memory():
    mem = load_memory()
    return mem
