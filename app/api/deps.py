from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.api_key import APIKey
import hashlib
import os


def get_merchant_by_api_key(x_api_key: str | None = Header(None), db: Session = Depends(get_db)):
    """Dependency to resolve merchant (user) from X-API-Key header.

    The API key is expected as a plaintext token; we store SHA256 hashes in DB.
    Returns the `user_id` (merchant id) if found.
    """
    if not x_api_key:
        # allow missing API key in dev/testing unless explicitly required
        if os.environ.get("REQUIRE_API_KEY", "0") == "1":
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")
        return None
    # allow keys with prefix like 'live_sk_...'
    token = x_api_key.strip()
    # compute hash
    h = hashlib.sha256(token.encode("utf-8")).hexdigest()
    ak = db.query(APIKey).filter(APIKey.key_hash == h).first()
    if not ak:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Return merchant id (user id)
    return ak.user_id
