"""Database storage for invoices, checkout sessions, payments, blockchain transactions,
users, API keys and uploaded/generated files (logos, invoice PDFs).

Replaces the old invoices.json / sessions.json / users.json / api_keys.json files and the
files written to DATA_DIR. Invoices and sessions keep their
original dict shape (stored whole in a JSON column) so existing endpoints work unchanged;
the frequently filtered fields are mirrored into real columns.

Payments and blockchain transactions have unique keys, so recording the same payment or
transaction twice is a no-op: claim_payment()/claim_blockchain_tx() return False the
second time and nothing changes.
"""
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy import (
    JSON, Column, DateTime, Integer, LargeBinary, MetaData, String, Table, UniqueConstraint,
    create_engine, delete, insert, select, update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

log = logging.getLogger("store")

metadata = MetaData()

invoices_table = Table(
    "store_invoices", metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True),  # keeps insertion order
    Column("id", String(64), nullable=False, unique=True),
    Column("type", String(32), nullable=True),
    Column("invoice_number", String(64), nullable=True, index=True),
    Column("merchant_id", String(64), nullable=True, index=True),
    Column("created_by", String(128), nullable=True, index=True),
    Column("status", String(32), nullable=True, index=True),
    Column("created_at", String(40), nullable=True),
    Column("data", JSON, nullable=False),
)

sessions_table = Table(
    "store_checkout_sessions", metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True),
    Column("id", String(64), nullable=False, unique=True),
    Column("merchant_id", String(64), nullable=True, index=True),
    Column("status", String(32), nullable=True, index=True),
    Column("created_at", String(40), nullable=True),
    Column("data", JSON, nullable=False),
)

payments_table = Table(
    "store_payments", metadata,
    Column("id", String(36), primary_key=True),
    Column("provider", String(32), nullable=False),
    Column("provider_ref", String(255), nullable=False),
    Column("invoice_id", String(64), nullable=True, index=True),
    Column("session_id", String(64), nullable=True, index=True),
    Column("amount", String(64), nullable=True),  # string to avoid float rounding
    Column("currency", String(16), nullable=True),
    Column("status", String(32), nullable=False, default="recorded"),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("data", JSON, nullable=True),
    UniqueConstraint("provider", "provider_ref", name="uq_store_payments_provider_ref"),
)

blockchain_tx_table = Table(
    "store_blockchain_transactions", metadata,
    Column("id", String(36), primary_key=True),
    Column("tx_hash", String(255), nullable=False, unique=True),  # normalised lower-case
    Column("chain", String(64), nullable=True),
    Column("invoice_id", String(64), nullable=True, index=True),
    Column("session_id", String(64), nullable=True, index=True),
    Column("amount", String(64), nullable=True),
    Column("status", String(32), nullable=False, default="recorded"),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("data", JSON, nullable=True),
)

users_table = Table(
    "store_users", metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True),
    Column("id", String(64), nullable=False, unique=True),
    Column("name", String(255), nullable=False, unique=True),
    Column("role", String(32), nullable=True),
    Column("data", JSON, nullable=False),
)

api_keys_table = Table(
    "store_api_keys", metadata,
    Column("seq", Integer, primary_key=True, autoincrement=True),
    Column("id", String(64), nullable=False, unique=True),
    Column("user_id", String(64), nullable=True, index=True),
    Column("key_hash", String(128), nullable=True, index=True),
    Column("data", JSON, nullable=False),
)

files_table = Table(
    "store_files", metadata,
    Column("name", String(255), primary_key=True),  # e.g. logos/merchant-5-logo.png
    Column("content_type", String(100), nullable=False),
    Column("content", LargeBinary, nullable=False),
    Column("updated_at", DateTime, nullable=False, default=datetime.utcnow),
)

store_meta_table = Table(
    "store_meta", metadata,
    Column("key", String(64), primary_key=True),
    Column("value", String(255), nullable=True),
)

_engine: Optional[Engine] = None
_engine_url: Optional[str] = None
_init_lock = threading.Lock()


def _normalise_url(url: str) -> str:
    # Railway/Heroku style URLs use postgres://, which SQLAlchemy 2 does not accept.
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def database_url(data_dir: Path) -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return _normalise_url(url)
    # Local development without DATABASE_URL: a SQLite file next to the other data.
    return f"sqlite:///{(data_dir / 'app.db').as_posix()}"


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("store.init() has not been called")
    return _engine


def init(data_dir: Path, is_prod: bool, import_sources: Iterable[Path] = ()) -> None:
    """Connect, create tables and run the one-time import of the old JSON files."""
    global _engine, _engine_url
    with _init_lock:
        url = database_url(data_dir)
        if _engine is not None:
            if url == _engine_url:
                return
            _engine.dispose()  # re-initialised with another database (tests reload main)
            _engine = None
        if is_prod and not url.startswith("postgresql"):
            raise RuntimeError(
                "DATABASE_URL must point to PostgreSQL in production "
                "(set it to ${{Postgres.DATABASE_URL}} in Railway)."
            )
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if url in ("sqlite://", "sqlite:///:memory:"):
                # In-memory SQLite is per connection: share one so all requests see the tables.
                kwargs["poolclass"] = StaticPool
        engine = create_engine(url, **kwargs)
        metadata.create_all(engine)
        _engine = engine
        _engine_url = url
        _import_json_once(list(import_sources))
        _import_users_once(list(import_sources))


# ---------------------------------------------------------------------------
# Invoices and sessions (dict documents)
# ---------------------------------------------------------------------------

def _clean(doc: dict) -> dict:
    # Same serialisation rules as the old json files (datetimes become strings).
    return json.loads(json.dumps(doc, default=str))


def _s(value) -> Optional[str]:
    return None if value is None else str(value)


def _invoice_columns(doc: dict) -> dict:
    return {
        "type": _s(doc.get("type")),
        "invoice_number": _s(doc.get("invoice_number") or doc.get("credit_note_number")),
        "merchant_id": _s(doc.get("merchant_id")),
        "created_by": _s(doc.get("created_by")),
        "status": _s(doc.get("status")),
        "created_at": _s(doc.get("created_at")),
    }


def _session_columns(doc: dict) -> dict:
    return {
        "merchant_id": _s(doc.get("merchant_id")),
        "status": _s(doc.get("status")),
        "created_at": _s(doc.get("created_at")),
    }


def _load(table) -> List[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(select(table.c.data).order_by(table.c.seq)).all()
    return [dict(r.data) for r in rows]


class StoreConflict(RuntimeError):
    """Two requests created different records with the same id at the same time."""


def _save(table, docs: List[dict], columns, identity=None) -> None:
    """Upsert every document in `docs` by id. Documents not in the list are left alone,
    so a request working on an older list cannot drop records added meanwhile; deletes
    go through delete_user()/delete_api_key().

    `identity(doc)` returns what makes a record *that* record (e.g. the username). An
    update whose identity differs from the stored one means two requests picked the same
    new id concurrently; that raises StoreConflict instead of overwriting the other record."""
    cleaned = []
    for doc in docs:
        if not doc.get("id"):
            doc["id"] = str(uuid.uuid4())
        cleaned.append(_clean(doc))
    with get_engine().begin() as conn:
        existing = {r.id: r.data for r in conn.execute(select(table.c.id, table.c.data))}
        for doc in cleaned:
            doc_id = str(doc["id"])
            if doc_id not in existing:
                conn.execute(insert(table).values(id=doc_id, data=doc, **columns(doc)))
            elif existing[doc_id] != doc:
                if identity and identity(existing[doc_id]) != identity(doc):
                    raise StoreConflict(f"{table.name}: id {doc_id} is already used by another record")
                conn.execute(update(table).where(table.c.id == doc_id).values(data=doc, **columns(doc)))


def load_invoices() -> List[dict]:
    return _load(invoices_table)


def save_invoices(invoices: List[dict]) -> None:
    _save(invoices_table, invoices, _invoice_columns)


def load_sessions() -> List[dict]:
    return _load(sessions_table)


def save_sessions(sessions: List[dict]) -> None:
    _save(sessions_table, sessions, _session_columns)


# ---------------------------------------------------------------------------
# Users and API keys
# ---------------------------------------------------------------------------

def _user_columns(doc: dict) -> dict:
    return {"name": str(doc.get("name")), "role": _s(doc.get("role"))}


def _api_key_columns(doc: dict) -> dict:
    return {"user_id": _s(doc.get("user_id") or doc.get("merchant_id")), "key_hash": _s(doc.get("key_hash"))}


def load_users() -> List[dict]:
    return _load(users_table)


def save_users(users: List[dict]) -> None:
    _save(users_table, users, _user_columns, identity=lambda d: d.get("name"))


def delete_user(user_id) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(users_table).where(users_table.c.id == str(user_id)))


def load_api_keys() -> List[dict]:
    return _load(api_keys_table)


def save_api_keys(keys: List[dict]) -> None:
    _save(api_keys_table, keys, _api_key_columns,
          identity=lambda d: d.get("key_hash") or d.get("key"))


def delete_api_key(key_id) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(api_keys_table).where(api_keys_table.c.id == str(key_id)))


# ---------------------------------------------------------------------------
# Files (merchant logos, generated invoice PDFs)
# ---------------------------------------------------------------------------

def put_file(name: str, content: bytes, content_type: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(files_table).where(files_table.c.name == name))
        conn.execute(insert(files_table).values(name=name, content=content, content_type=content_type,
                                                updated_at=datetime.utcnow()))


def get_file(name: str) -> Optional[dict]:
    with get_engine().connect() as conn:
        row = conn.execute(select(files_table).where(files_table.c.name == name)).mappings().first()
    return dict(row) if row else None


def delete_file(name: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(files_table).where(files_table.c.name == name))


# ---------------------------------------------------------------------------
# Payments and blockchain transactions (record once)
# ---------------------------------------------------------------------------

def normalise_tx_hash(tx_hash: str) -> str:
    return str(tx_hash).strip().lower()


def claim_payment(provider: str, provider_ref, *, invoice_id=None, session_id=None,
                  amount=None, currency=None, data: Optional[dict] = None) -> bool:
    """Record a payment. Returns False (and changes nothing) if this provider reference
    was already recorded."""
    if not provider_ref:
        return True  # nothing to deduplicate on
    try:
        with get_engine().begin() as conn:
            conn.execute(insert(payments_table).values(
                id=str(uuid.uuid4()), provider=provider, provider_ref=str(provider_ref),
                invoice_id=_s(invoice_id), session_id=_s(session_id),
                amount=_s(amount), currency=_s(currency), status="recorded",
                created_at=datetime.utcnow(), data=_clean(data or {}),
            ))
        return True
    except IntegrityError:
        return False


def release_payment(provider: str, provider_ref) -> None:
    """Undo claim_payment when the rest of the processing failed, so a retry can succeed."""
    if not provider_ref:
        return
    with get_engine().begin() as conn:
        conn.execute(delete(payments_table).where(
            payments_table.c.provider == provider,
            payments_table.c.provider_ref == str(provider_ref),
        ))


def claim_blockchain_tx(tx_hash, *, chain=None, invoice_id=None, session_id=None,
                        amount=None, data: Optional[dict] = None) -> bool:
    """Record a blockchain transaction. Returns False (and changes nothing) if this
    transaction hash was already recorded."""
    if not tx_hash:
        return True
    try:
        with get_engine().begin() as conn:
            conn.execute(insert(blockchain_tx_table).values(
                id=str(uuid.uuid4()), tx_hash=normalise_tx_hash(tx_hash), chain=_s(chain),
                invoice_id=_s(invoice_id), session_id=_s(session_id), amount=_s(amount),
                status="recorded", created_at=datetime.utcnow(), data=_clean(data or {}),
            ))
        return True
    except IntegrityError:
        return False


def release_blockchain_tx(tx_hash) -> None:
    if not tx_hash:
        return
    with get_engine().begin() as conn:
        conn.execute(delete(blockchain_tx_table).where(
            blockchain_tx_table.c.tx_hash == normalise_tx_hash(tx_hash)))


def list_payments() -> List[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(select(payments_table).order_by(payments_table.c.created_at)).mappings().all()
    return [dict(r) for r in rows]


def list_blockchain_txs() -> List[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(select(blockchain_tx_table).order_by(blockchain_tx_table.c.created_at)).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# One-time import of the old JSON files
# ---------------------------------------------------------------------------

# Invoice fields that reference a payment at a provider.
_PROVIDER_REF_FIELDS = (
    ("stripe", "stripe_intent_id"),
    ("paypal", "paypal_capture_id"),
    ("coinbase", "coinbase_charge_id"),
    ("onecom", "onecom_txn_id"),
)


def _read_json_list(path: Path) -> List[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except Exception as exc:  # corrupt file: log and keep going, never crash startup
        log.warning("store: could not read %s: %s", path, exc)
        return []


def _import_json_once(sources: List[Path]) -> None:
    """Import invoices.json / sessions.json from each source directory, once.

    Records are matched by id, so running it against several directories (DATA_DIR and the
    repo copy) never creates duplicates. A marker row prevents re-importing later, which
    would otherwise resurrect records changed or removed in the database.
    """
    engine = get_engine()
    with engine.connect() as conn:
        done = conn.execute(select(store_meta_table.c.value).where(
            store_meta_table.c.key == "json_import_done")).scalar()
    if done:
        return

    invoices, sessions = [], []
    seen_inv, seen_sess = set(), set()
    for src in sources:
        for doc in _read_json_list(src / "invoices.json"):
            if doc.get("id") is not None and str(doc["id"]) not in seen_inv:
                seen_inv.add(str(doc["id"]))
                invoices.append(doc)
        for doc in _read_json_list(src / "sessions.json"):
            if doc.get("id") is not None and str(doc["id"]) not in seen_sess:
                seen_sess.add(str(doc["id"]))
                sessions.append(doc)

    try:
        save_invoices(invoices)
        save_sessions(sessions)
    except IntegrityError:
        # Another worker is importing at the same moment; it will finish the job.
        log.warning("store: JSON import already running in another worker")
        return

    # Back-fill payment records so a replayed webhook for an old payment is deduplicated.
    for inv in invoices:
        for provider, field in _PROVIDER_REF_FIELDS:
            if inv.get(field):
                claim_payment(provider, inv[field], invoice_id=inv.get("id"),
                              session_id=inv.get("session_id"), amount=inv.get("amount") or inv.get("total"),
                              currency=inv.get("currency"), data={"imported": True})
        if inv.get("blockchain_tx_id"):
            claim_blockchain_tx(inv["blockchain_tx_id"], chain=inv.get("blockchain_network"),
                                invoice_id=inv.get("id"), session_id=inv.get("session_id"),
                                amount=inv.get("amount") or inv.get("total"), data={"imported": True})

    try:
        with engine.begin() as conn:
            conn.execute(insert(store_meta_table).values(
            key="json_import_done",
                value=f"{datetime.utcnow().isoformat()} invoices={len(invoices)} sessions={len(sessions)}",
            ))
    except IntegrityError:
        return
    log.warning("store: imported %d invoices and %d sessions from JSON", len(invoices), len(sessions))


def _import_users_once(sources: List[Path]) -> None:
    """Import users.json / api_keys.json once (first source wins per id and name)."""
    engine = get_engine()
    with engine.connect() as conn:
        done = conn.execute(select(store_meta_table.c.value).where(
            store_meta_table.c.key == "json_users_import_done")).scalar()
    if done:
        return

    users, keys = [], []
    seen_ids, seen_names, seen_keys = set(), set(), set()
    for src in sources:
        for doc in _read_json_list(src / "users.json"):
            if doc.get("id") is None or not doc.get("name"):
                continue
            if str(doc["id"]) in seen_ids or str(doc["name"]) in seen_names:
                continue
            seen_ids.add(str(doc["id"]))
            seen_names.add(str(doc["name"]))
            users.append(doc)
        for doc in _read_json_list(src / "api_keys.json"):
            if doc.get("id") is not None and str(doc["id"]) not in seen_keys:
                seen_keys.add(str(doc["id"]))
                keys.append(doc)

    try:
        save_users(users)
        save_api_keys(keys)
        with engine.begin() as conn:
            conn.execute(insert(store_meta_table).values(
                key="json_users_import_done",
                value=f"{datetime.utcnow().isoformat()} users={len(users)} api_keys={len(keys)}",
            ))
    except IntegrityError:
        log.warning("store: user import already running in another worker")
        return
    log.warning("store: imported %d users and %d API keys from JSON", len(users), len(keys))
