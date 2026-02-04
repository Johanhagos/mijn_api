from typing import Optional, Dict
from contextlib import contextmanager
from app.db.session import SessionLocal
from app.models.hosted_session import HostedSession


@contextmanager
def _db():
    try:
        db = SessionLocal()
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


def create_session(session_dict: Dict) -> Dict:
    with _db() as db:
        s = HostedSession(
            id=session_dict.get("id"),
            merchant_id=str(session_dict.get("merchant_id")) if session_dict.get("merchant_id") is not None else None,
            amount=session_dict.get("amount", 0),
            mode=session_dict.get("mode", "test"),
            status=session_dict.get("status", "created"),
            success_url=session_dict.get("success_url"),
            cancel_url=session_dict.get("cancel_url"),
            url=session_dict.get("url"),
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return {
            "id": s.id,
            "merchant_id": s.merchant_id,
            "amount": float(s.amount),
            "mode": s.mode,
            "status": s.status,
            "success_url": s.success_url,
            "cancel_url": s.cancel_url,
            "url": s.url,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }


def get_session(session_id: str) -> Optional[Dict]:
    with _db() as db:
        s = db.query(HostedSession).filter(HostedSession.id == session_id).first()
        if not s:
            return None
        return {
            "id": s.id,
            "merchant_id": s.merchant_id,
            "amount": float(s.amount),
            "mode": s.mode,
            "status": s.status,
            "success_url": s.success_url,
            "cancel_url": s.cancel_url,
            "url": s.url,
            "payment_system": s.payment_system,
            "blockchain_tx_id": s.blockchain_tx_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "paid_at": s.paid_at.isoformat() if s.paid_at else None,
        }


def update_session(session_id: str, updates: Dict) -> Optional[Dict]:
    with _db() as db:
        s = db.query(HostedSession).filter(HostedSession.id == session_id).first()
        if not s:
            return None
        for k, v in updates.items():
            if hasattr(s, k):
                setattr(s, k, v)
        db.add(s)
        db.commit()
        db.refresh(s)
        return get_session(session_id)
