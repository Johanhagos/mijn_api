from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Any, Dict
import os
import subprocess
from pathlib import Path
from typing import Optional

from .vat_store import list_countries, get_country_record, update_country_record
from pathlib import Path
import json

# Path to api keys (mirrors main app behaviour)
DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp"))
API_KEYS_FILE = DATA_DIR / "api_keys.json"
from .ai_integration import format_vat_summary

router = APIRouter()


class CountryVAT(BaseModel):
    name: str | None = None
    standard_rate: float | None = None
    reduced_rates: dict | None = None
    notes: str | None = None


def _is_admin(api_key: str | None) -> bool:
    """Simple admin check against env var VAT_ADMIN_KEY (dev helper)."""
    # First, check explicit VAT_ADMIN_KEY env var
    env_key = os.getenv("VAT_ADMIN_KEY")
    if env_key:
        return api_key == env_key

    # Fallback: check api_keys.json for an entry with matching key and role 'admin'
    try:
        if API_KEYS_FILE.exists():
            text = API_KEYS_FILE.read_text(encoding="utf-8").strip()
            keys = json.loads(text or "[]")
            # keys expected as list of objects {"key": "...", "role": "admin"}
            for entry in keys:
                if isinstance(entry, dict) and entry.get("key") == api_key and entry.get("role") == "admin":
                    return True
    except Exception:
        pass

    # Default safe behaviour: only allow updates in non-production when no admin key configured
    return os.getenv("RAILWAY_ENVIRONMENT") != "production"


@router.get("/vat", summary="List VAT compliance records")
async def vat_list():
    return list_countries()


@router.get("/vat/{country}", summary="Get VAT record for country code")
async def vat_get(country: str):
    rec = get_country_record(country)
    if not rec:
        raise HTTPException(status_code=404, detail="Country not found")
    return rec


@router.put("/vat/{country}", summary="Create or update VAT record")
async def vat_put(country: str, payload: CountryVAT, x_vat_admin_key: str | None = Header(None)):
    if not _is_admin(x_vat_admin_key):
        raise HTTPException(status_code=403, detail="Forbidden")
    record: Dict[str, Any] = payload.dict(exclude_none=True)
    if not record:
        raise HTTPException(status_code=400, detail="Empty payload")
    saved = update_country_record(country, record)
    return {"country": country.upper(), "record": saved}
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


@router.get("/vat/summary/{country}", summary="AI-formatted VAT summary for a country")
async def vat_summary(country: str):
    return format_vat_summary(country)


def _get_git_commit_short() -> Optional[str]:
    """Try to get the current git commit short hash. Returns None if unavailable."""
    try:
        # Try git command first
        completed = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        commit = completed.stdout.strip()
        if commit:
            return commit
    except Exception:
        pass

    # Fallback: read .git/HEAD and resolve ref
    try:
        repo_root = Path(__file__).resolve().parents[1]
        head = (repo_root / ".git" / "HEAD")
        if head.exists():
            ref = head.read_text(encoding="utf-8").strip()
            if ref.startswith("ref:"):
                ref_path = ref.split(" ", 1)[1].strip()
                ref_file = repo_root / ".git" / ref_path
                if ref_file.exists():
                    return ref_file.read_text(encoding="utf-8").strip()[:8]
            else:
                # HEAD directly contains commit
                return ref[:8]
    except Exception:
        pass

    return None


@router.get("/commit", summary="Get agent code commit short hash")
async def commit_status():
    commit = _get_git_commit_short()
    if not commit:
        return {"commit": None, "status": "unknown", "note": "git info unavailable on this deployment"}
    return {"commit": commit, "status": "ok"}
