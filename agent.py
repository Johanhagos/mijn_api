"""Invoice System Assistant (LangChain agent)

Run locally after installing requirements and setting `OPENAI_API_KEY`.

Features:
- Ingests key repo files into a FAISS vectorstore (local) using OpenAI embeddings
- Provides a retrieval QA chain and some callable tools:
  - `calculate_vat` uses `vat_engine.py` to compute VAT for given invoice-like payloads
  - `query_db` runs a safe SQL query against `DATABASE_URL` (read-only, limited)
  - `fetch_pdf_hash` downloads an S3 object and returns SHA256
  - `check_tx` placeholder for blockchain tx status (uses Web3 if configured)

Usage:
  python agent.py --build (builds embeddings)
  python agent.py       (interactive REPL)

"""
import os
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import List

try:
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS
    from langchain.text_splitter import CharacterTextSplitter
    from langchain.llms import OpenAI
    from langchain.chains import RetrievalQA
    from langchain.tools import Tool
    from langchain.agents import initialize_agent, AgentType
    _HAS_LANGCHAIN = True
except Exception:
    # Allow importing this module in environments without langchain installed
    OpenAIEmbeddings = None
    FAISS = None
    CharacterTextSplitter = None
    OpenAI = None
    RetrievalQA = None
    Tool = None
    initialize_agent = None
    AgentType = None
    _HAS_LANGCHAIN = False

# Optional runtime tools
import boto3
from decimal import Decimal

# Local imports
try:
    from vat_engine import create_invoice, compute_vat_for_line
except Exception:
    create_invoice = None
    compute_vat_for_line = None

ROOT = Path(__file__).parent
KNOWLEDGE_FILES = [
    ROOT / "README_DEPLOY.md",
    ROOT / "main.py",
    ROOT / "models.py",
    ROOT / "vat_engine.py",
    ROOT / "Dockerfile.prod",
    ROOT / "docker-compose.prod.yml",
    ROOT / "nginx.conf",
    ROOT / "terraform" / "main.tf",
]

VECTORSTORE_PATH = ROOT / "vectorstore.faiss"


def load_documents(paths: List[Path]) -> List[str]:
    docs = []
    for p in paths:
        try:
            if p.is_dir():
                for f in sorted(p.glob("**/*")):
                    if f.is_file() and f.suffix in (".py", ".md", ".yml", ".yaml", ".tf", ".txt"):
                        docs.append(f.read_text(encoding="utf-8", errors="ignore"))
            else:
                if p.exists():
                    docs.append(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
    return docs


def build_vectorstore(openai_api_key: str):
    os.environ["OPENAI_API_KEY"] = openai_api_key
    docs = load_documents(KNOWLEDGE_FILES)
    if not docs:
        print("No documents found to ingest. Put docs in the repo or update KNOWLEDGE_FILES.")
        return None

    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = []
    for d in docs:
        chunks.extend(splitter.split_text(d))

    embeddings = OpenAIEmbeddings()
    store = FAISS.from_texts(chunks, embeddings)
    store.save_local(str(VECTORSTORE_PATH))
    print(f"Saved vectorstore to {VECTORSTORE_PATH}")
    return store


def load_vectorstore(openai_api_key: str):
    os.environ["OPENAI_API_KEY"] = openai_api_key
    if not VECTORSTORE_PATH.exists():
        return None
    embeddings = OpenAIEmbeddings()
    store = FAISS.load_local(str(VECTORSTORE_PATH), embeddings)
    return store


# Tools

def tool_calculate_vat(payload_json: str) -> str:
    """Call into local vat_engine to compute VAT for provided payload.

    payload_json: JSON string with {shop_id, customer_id, items:[{qty, unit_price, vat_rate, product_name}], ...}
    """
    if compute_vat_for_line is None:
        return "VAT engine not available in this environment."
    try:
        payload = json.loads(payload_json)
    except Exception as e:
        return f"Invalid JSON: {e}"

    # For quick computation, compute line VATs and totals using compute_vat_for_line
    shop = payload.get("shop") or {}
    customer = payload.get("customer") or {}
    items = payload.get("items") or []

    subtotal = Decimal("0.00")
    vat_total = Decimal("0.00")

    for it in items:
        qty = int(it.get("qty", 1))
        unit_price = Decimal(str(it.get("unit_price", "0")))
        vat_rate = Decimal(str(it.get("vat_rate", "0")))
        line = (unit_price * qty).quantize(Decimal("0.01"))
        # compute_vat_for_line signature differs; best-effort fallback
        try:
            v = compute_vat_for_line(shop, customer, unit_price, qty, vat_rate)
            v = Decimal(str(v))
        except Exception:
            v = (line * vat_rate / Decimal("100")).quantize(Decimal("0.01"))
        subtotal += line
        vat_total += v

    total = (subtotal + vat_total).quantize(Decimal("0.01"))
    return json.dumps({"subtotal": str(subtotal), "vat_total": str(vat_total), "total": str(total)})


def tool_query_db(sql: str) -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return "DATABASE_URL not set"
    # Safety: only allow SELECT and limit to known tables
    if not sql.strip().lower().startswith("select"):
        return "Only SELECT queries are allowed via this tool."
    # Simple whitelist of tables that can be queried
    allowed_tables = {"shops", "users", "customers", "products", "invoices", "invoice_items", "audit_logs", "tax_rates", "payments"}
    # find referenced tables via simple regex on FROM and JOIN clauses
    tbls = re.findall(r"(?:from|join)\s+([\w\.]+)", sql, flags=re.IGNORECASE)
    found = {t.split('.')[-1] for t in tbls}
    if found and not (found <= allowed_tables):
        return f"Query references disallowed tables: {found - allowed_tables}"
    try:
        # Import SQLAlchemy lazily to avoid import-time issues in constrained envs
        from sqlalchemy import create_engine, text
        # Enforce a safe limit
        if "limit" not in sql.lower():
            sql = sql.rstrip(";") + " LIMIT 100"
        engine = create_engine(db_url)
        with engine.connect() as conn:
            res = conn.execute(text(sql)).fetchall()
            rows = [dict(r._mapping) for r in res]
            return json.dumps(rows, default=str)
    except Exception as e:
        return f"DB error: {e}"


def tool_fetch_pdf_hash(s3_path: str) -> str:
    # supports s3://bucket/key and file://local/path
    try:
        if s3_path.startswith("s3://"):
            _, _, rest = s3_path.partition("s3://")
            bucket, _, key = rest.partition("/")
            s3 = boto3.client("s3")
            obj = s3.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
        elif s3_path.startswith("file://"):
            _, _, local = s3_path.partition("file://")
            p = Path(local)
            if not p.exists():
                return f"Local file not found: {local}"
            body = p.read_bytes()
        else:
            return "Path must be s3://bucket/key or file://path"

        h = hashlib.sha256(body).hexdigest()
        return json.dumps({"path": s3_path, "sha256": h})
    except Exception as e:
        return f"Fetch error: {e}"


def tool_check_tx(tx_hash: str) -> str:
    # Placeholder: if WEB3_PROVIDER env set, check via web3; otherwise return mock
    provider = os.getenv("WEB3_PROVIDER")
    if not provider:
        return json.dumps({"tx": tx_hash, "status": "UNKNOWN", "note": "Set WEB3_PROVIDER to enable real checks"})
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(provider))
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        return json.dumps({"tx": tx_hash, "status": "CONFIRMED" if receipt else "PENDING", "receipt": dict(receipt)})
    except Exception as e:
        return f"Web3 error: {e}"


def tool_fetch_invoice(identifier: str) -> str:
    """Fetch invoice by invoice_number or id from the database and return JSON.

    identifier: invoice_number (text) or UUID id
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return "DATABASE_URL not set"
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Try invoice_number first
            q = text("select * from invoices where invoice_number = :id limit 1")
            res = conn.execute(q, {"id": identifier}).fetchone()
            if not res:
                q2 = text("select * from invoices where id = :id limit 1")
                res = conn.execute(q2, {"id": identifier}).fetchone()
            if not res:
                return json.dumps({"error": "invoice not found"})
            invoice = dict(res._mapping)
            # fetch items
            items = conn.execute(text("select * from invoice_items where invoice_id = :iid"), {"iid": invoice.get("id")}).fetchall()
            invoice_items = [dict(r._mapping) for r in items]
            invoice["items"] = invoice_items
            return json.dumps(invoice, default=str)
    except Exception as e:
        return f"DB error: {e}"


def tool_refresh_vectorstore(openai_key: str = None) -> str:
    key = openai_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return "OpenAI key required"
    try:
        store = build_vectorstore(key)
        if store is None:
            return "Failed to build vectorstore"
        return f"Vectorstore rebuilt and saved to {VECTORSTORE_PATH}"
    except Exception as e:
        return f"Error: {e}"


def tool_fetch_invoice_full(identifier: str) -> str:
    """Fetch invoice, compute/fetch PDF hash, and check payment tx in one call.

    Returns JSON with keys: invoice, pdf_hash (or error), payment_tx (or null), tx_status (or note).
    """
    try:
        inv_res = tool_fetch_invoice(identifier)
        # tool_fetch_invoice returns JSON string or error
        try:
            inv = json.loads(inv_res)
        except Exception:
            return json.dumps({"error": f"Failed to load invoice: {inv_res}"})

        result = {"invoice": inv}

        # PDF hash
        pdf_url = inv.get("pdf_url")
        if pdf_url:
            pdf_hash_res = tool_fetch_pdf_hash(pdf_url)
            try:
                result["pdf_hash"] = json.loads(pdf_hash_res)
            except Exception:
                result["pdf_hash"] = {"error": pdf_hash_res}
        else:
            result["pdf_hash"] = None

        # Payment tx: check common fields or payments table
        tx = inv.get("payment_tx") or inv.get("tx_hash") or inv.get("transaction_hash")
        if not tx:
            # try payments table
            if inv.get("id"):
                q = f"SELECT tx_hash FROM payments WHERE invoice_id = '{inv.get('id')}' ORDER BY created_at DESC LIMIT 1"
                pay_res = tool_query_db(q)
                try:
                    pay_list = json.loads(pay_res)
                    if isinstance(pay_list, list) and len(pay_list) > 0:
                        tx = pay_list[0].get("tx_hash") or pay_list[0].get("tx")
                except Exception:
                    tx = None

        result["payment_tx"] = tx

        if tx:
            tx_status_res = tool_check_tx(tx)
            try:
                result["tx_status"] = json.loads(tx_status_res)
            except Exception:
                result["tx_status"] = {"raw": tx_status_res}
        else:
            result["tx_status"] = {"status": "none"}

        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def make_tools():
    return [
        Tool(name="calculate_vat", func=tool_calculate_vat, description="Calculate VAT given invoice payload JSON."),
        Tool(name="query_db", func=tool_query_db, description="Run a read-only SELECT SQL query against DATABASE_URL."),
        Tool(name="fetch_pdf_hash", func=tool_fetch_pdf_hash, description="Fetch S3 or local file and return its SHA256 hash. Arg: s3://bucket/key or file://path"),
        Tool(name="fetch_invoice", func=tool_fetch_invoice, description="Fetch invoice by invoice_number or id from the database and return JSON."),
        Tool(name="refresh_vectorstore", func=tool_refresh_vectorstore, description="Rebuild embeddings/vectorstore; pass OpenAI key or set OPENAI_API_KEY env."),
        Tool(name="fetch_invoice_full", func=tool_fetch_invoice_full, description="Fetch invoice, PDF hash, and payment tx status in one call."),
        Tool(name="check_tx", func=tool_check_tx, description="Check blockchain transaction status by tx hash."),
    ]


def build_agent(retriever, openai_api_key: str):
    os.environ["OPENAI_API_KEY"] = openai_api_key
    llm = OpenAI(temperature=0)
    tools = make_tools()
    agent = initialize_agent(
        tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=False
    )
    return agent


def interactive(agent, retriever):
    qa = RetrievalQA.from_chain_type(llm=agent.llm, chain_type="stuff", retriever=retriever)
    print("Agent ready. Enter questions (type 'exit' to quit).")
    while True:
        q = input("Q> ")
        if not q:
            continue
        if q.strip().lower() in ("exit", "quit"):
            break
        # If user wants to run a tool explicitly, agent.run will handle
        try:
            ans = qa.run(q)
            print(ans)
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build embeddings/vectorstore from repo files")
    parser.add_argument("--openai-key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key")
    args = parser.parse_args()

    if not args.openai_key:
        print("OPENAI API key required (set --openai-key or OPENAI_API_KEY env)")
        return

    store = None
    if args.build:
        store = build_vectorstore(args.openai_key)
    else:
        store = load_vectorstore(args.openai_key)
        if store is None:
            print("Vectorstore not found. Run with --build to create it.")
            return

    retriever = store.as_retriever(search_kwargs={"k": 4})
    agent = build_agent(retriever, args.openai_key)

    # Interactive loop
    interactive(agent, retriever)


if __name__ == "__main__":
    main()
