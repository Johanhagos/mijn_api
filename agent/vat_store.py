from pathlib import Path
import json
import threading
import os
from typing import Dict, Any

# Determine data dir the same way main app does (fall back to /tmp)
DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp"))
VAT_FILE = DATA_DIR / "vat_compliance.json"

# In-process lock for writes (single-process apps)
_lock = threading.Lock()


def load_vat_data() -> Dict[str, Any]:
    """Load VAT compliance data from disk. Returns an empty dict if file missing or invalid."""
    try:
        if not VAT_FILE.exists():
            return {}
        text = VAT_FILE.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)
    except Exception:
        return {}


def save_vat_data(data: Dict[str, Any]) -> None:
    """Atomically save VAT compliance data to disk."""
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = VAT_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(VAT_FILE)


def get_country_record(country_code: str) -> Dict[str, Any]:
    data = load_vat_data()
    return data.get(country_code.upper(), {})


def update_country_record(country_code: str, record: Dict[str, Any]) -> Dict[str, Any]:
    data = load_vat_data()
    data[country_code.upper()] = record
    save_vat_data(data)
    return record


def list_countries() -> Dict[str, Any]:
    return load_vat_data()
