#!/usr/bin/env python3
"""
Migration/import script:
- Create DB tables (if missing)
- Import users from users.json into `users` table (password hashes preserved)
- Create an API key for each user with role 'admin' or 'merchant' and print the plaintext key
- Add `merchant_id` column to `invoices` if the DB supports ALTER TABLE (Postgres). For sqlite, instruct the user.

Usage:
  DATABASE_URL=postgres://... python scripts/migrate_users_and_add_merchant.py
"""
import os
import json
import hashlib
import secrets
from sqlalchemy import text
from app.db.session import engine, SessionLocal, Base
from app.models.user import User
from app.models.api_key import APIKey
from sqlalchemy.exc import IntegrityError

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")

print("Using DATABASE_URL:", DB_URL)

# create tables (will create new tables but won't alter existing ones)
Base.metadata.create_all(bind=engine)

# load users.json
here = os.path.dirname(os.path.dirname(__file__))
users_file = os.path.join(here, "users.json")
if not os.path.exists(users_file):
    print("users.json not found at", users_file)
else:
    with open(users_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        for u in data:
            username = u.get("name") or u.get("username")
            pwd_hash = u.get("password")
            role = u.get("role", "user")
            # preserve existing hashed password value
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                print(f"User {username} already exists, skipping")
                continue
            new = User(username=username, password_hash=pwd_hash, role=role)
            db.add(new)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                print(f"Could not insert {username}, skipping")
                continue
            db.refresh(new)
            print(f"Inserted user {username} (id={new.id}, role={role})")
            # if admin/merchant, create an API key for them
            if role in ("admin", "merchant"):
                token = "live_sk_" + secrets.token_urlsafe(24)
                key_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                ak = APIKey(user_id=new.id, key_hash=key_hash, label="initial-import")
                db.add(ak)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    print(f"Could not create API key for {username}")
                    continue
                print(f"API key for {username}: {token}")
    finally:
        db.close()

# Add merchant_id column to invoices for Postgres
dialect = engine.dialect.name
print("DB dialect:", dialect)
if dialect in ("postgresql", "postgres"):
    with engine.connect() as conn:
        # check if column exists
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='invoices' and column_name='merchant_id'"))
        if res.first():
            print("merchant_id column already exists on invoices")
        else:
            print("Adding merchant_id column to invoices (postgres)")
            conn.execute(text("ALTER TABLE invoices ADD COLUMN merchant_id INTEGER REFERENCES users(id)"))
            print("Added merchant_id column")
else:
    print("Automatic addition of merchant_id is only supported for Postgres in this script.")
    print("If you are using sqlite, please run a schema migration (alembic) or recreate the DB with the updated models.")

print("Done.")
