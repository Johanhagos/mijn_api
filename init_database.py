#!/usr/bin/env python3
"""
Database initialization script for PostgreSQL migration
Run this once to create tables and migrate existing JSON data
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, SessionLocal
from models import Shop, User, Customer
from db_migration_helpers import (
    migrate_users_from_json,
    migrate_invoices_from_json,
    get_or_create_default_customer
)
import hashlib


def main():
    print("🚀 Initializing database tables...")
    
    # Create all tables
    init_db()
    print("✅ Tables created")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Check if default shop exists
        shop = db.query(Shop).first()
        
        if not shop:
            print("📦 Creating default shop...")
            # Generate API key
            import secrets
            api_key = secrets.token_urlsafe(32)
            api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            shop = Shop(
                name="Default Organization",
                country="NL",
                address={"street": "", "city": "", "zip": "", "country": "NL"},
                currency="EUR",
                invoice_prefix="INV",
                api_key_hash=api_key_hash,
                plan="starter",
                email="admin@example.com"
            )
            db.add(shop)
            db.commit()
            db.refresh(shop)
            
            print(f"✅ Default shop created with ID: {shop.id}")
            print(f"🔑 API Key (save this!): {api_key}")
        else:
            print(f"✅ Using existing shop: {shop.name} (ID: {shop.id})")
        
        # Check for existing users
        user_count = db.query(User).count()
        if user_count == 0:
            print("👤 Migrating users from JSON...")
            users_file = Path(__file__).parent / "users.json"
            migrated_users = migrate_users_from_json(db, users_file, shop.id)
            print(f"✅ Migrated {len(migrated_users)} users")
        else:
            print(f"✅ Database already has {user_count} users")
        
        # Create or get default customer
        customer = get_or_create_default_customer(db, shop.id)
        print(f"✅ Default customer ready: {customer.name} (ID: {customer.id})")
        
        # Check for existing invoices
        from models import Invoice
        invoice_count = db.query(Invoice).count()
        if invoice_count == 0:
            print("📄 Migrating invoices from JSON...")
            invoices_file = Path(__file__).parent / "invoices.json"
            migrated_invoices = migrate_invoices_from_json(
                db, invoices_file, shop.id, customer.id
            )
            print(f"✅ Migrated {len(migrated_invoices)} invoices")
        else:
            print(f"✅ Database already has {invoice_count} invoices")
        
        print("\n✨ Database initialization complete!")
        print(f"Shop ID: {shop.id}")
        print(f"Users: {db.query(User).count()}")
        print(f"Invoices: {db.query(Invoice).count()}")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
