"""
Data Migration Script: JSON → PostgreSQL

Migrates existing data from users.json and invoices.json
into the new PHASE 1 multi-tenant database schema.

Usage:
    python migrate_json_to_postgres.py

This creates demo data in an organization if no data exists,
or migrates existing users and invoices to PostgreSQL.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from db import SessionLocal, engine
from models_phase1 import Base, Organization, User, Invoice
from auth import hash_password

# JSON file paths
USERS_JSON = Path(__file__).parent / "users.json"
INVOICES_JSON = Path(__file__).parent / "invoices.json"


def load_json_file(filepath: Path) -> list:
    """Load JSON file safely."""
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return []
    
    try:
        with open(filepath) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing {filepath}: {e}")
        return []


def create_user_from_old_format(db: Session, org: Organization, old_user: dict) -> User:
    """Convert old user format to new User model."""
    
    # Map old fields to new
    user = User(
        org_id=org.id,
        email=old_user.get("email") or old_user.get("name", "unknown") + "@example.com",
        password_hash=old_user.get("password_hash") or hash_password("temp_password_123"),
        name=old_user.get("name", "User"),
        role=old_user.get("role", "user"),
        email_verified=True,  # Auto-verify migrated users
        email_verified_at=datetime.now(timezone.utc),
        last_login=None,
    )
    
    return user


def migrate_users(db: Session) -> int:
    """Migrate users from users.json to PostgreSQL."""
    
    print("\n📥 Migrating users...")
    
    old_users = load_json_file(USERS_JSON)
    if not old_users:
        print("ℹ️  No users to migrate")
        return 0
    
    # Check if users already exist
    existing = db.query(User).count()
    if existing > 0:
        print(f"⚠️  Database already has {existing} users. Skipping migration.")
        return 0
    
    # Create default organization if none exists
    default_org = db.query(Organization).filter(
        Organization.slug == "default"
    ).first()
    
    if not default_org:
        default_org = Organization(
            name="Default Organization",
            slug="default",
            timezone="UTC",
            currency="EUR",
            subscription_tier="starter",
            subscription_status="active",
            owner_id=1  # Will update after creating first user
        )
        db.add(default_org)
        db.flush()
        print(f"✅ Created default organization: {default_org.slug}")
    
    # Migrate users
    migrated = 0
    for old_user in old_users:
        # Check if email already exists
        existing_user = db.query(User).filter(
            User.email == old_user.get("email"),
            User.org_id == default_org.id
        ).first()
        
        if not existing_user:
            user = create_user_from_old_format(db, default_org, old_user)
            db.add(user)
            migrated += 1
            print(f"  → Migrated: {user.name} ({user.email})")
    
    # Update org owner to first user
    first_user = db.query(User).filter(User.org_id == default_org.id).first()
    if first_user and default_org.owner_id != first_user.id:
        default_org.owner_id = first_user.id
    
    db.commit()
    print(f"✅ Migrated {migrated} users")
    return migrated


def migrate_invoices(db: Session) -> int:
    """Migrate invoices from invoices.json to PostgreSQL."""
    
    print("\n📥 Migrating invoices...")
    
    old_invoices = load_json_file(INVOICES_JSON)
    if not old_invoices:
        print("ℹ️  No invoices to migrate")
        return 0
    
    # Get default organization
    org = db.query(Organization).filter(Organization.slug == "default").first()
    if not org:
        print("❌ Default organization not found. Cannot migrate invoices.")
        return 0
    
    # Get first user (creator)
    creator = db.query(User).filter(User.org_id == org.id).first()
    if not creator:
        print("❌ No users found. Cannot migrate invoices.")
        return 0
    
    # Check if invoices already exist
    existing = db.query(Invoice).filter(Invoice.org_id == org.id).count()
    if existing > 0:
        print(f"⚠️  Organization already has {existing} invoices. Skipping migration.")
        return 0
    
    # Migrate invoices
    migrated = 0
    for old_invoice in old_invoices:
        
        # Map old format to new
        invoice = Invoice(
            org_id=org.id,
            number=old_invoice.get("number", f"INV-{migrated+1:04d}"),
            status=old_invoice.get("status", "draft"),
            created_by_id=creator.id,
            customer_email=old_invoice.get("customer_email", "unknown@example.com"),
            customer_name=old_invoice.get("customer_name", "Unknown"),
            customer_country=old_invoice.get("customer_country", "NL"),
            customer_vat_id=old_invoice.get("customer_vat_id"),
            amount_subtotal=int(old_invoice.get("amount_subtotal", 0) * 100),  # cents
            amount_tax=int(old_invoice.get("amount_tax", 0) * 100),
            amount_total=int(old_invoice.get("amount_total", 0) * 100),
            currency=old_invoice.get("currency", "EUR"),
            tax_rate=str(old_invoice.get("tax_rate", "21.0")),
            is_reverse_charge=old_invoice.get("is_reverse_charge", False),
            tax_breakdown=old_invoice.get("tax_breakdown"),
            line_items=old_invoice.get("line_items", []),
            notes=old_invoice.get("notes"),
            pdf_path=old_invoice.get("pdf_path"),
        )
        
        # Parse dates if present
        if old_invoice.get("finalized_at"):
            invoice.finalized_at = datetime.fromisoformat(old_invoice["finalized_at"].replace('Z', '+00:00'))
        if old_invoice.get("paid_at"):
            invoice.paid_at = datetime.fromisoformat(old_invoice["paid_at"].replace('Z', '+00:00'))
        if old_invoice.get("due_at"):
            invoice.due_at = datetime.fromisoformat(old_invoice["due_at"].replace('Z', '+00:00'))
        
        db.add(invoice)
        migrated += 1
        print(f"  → Migrated: {invoice.number}")
    
    db.commit()
    print(f"✅ Migrated {migrated} invoices")
    return migrated


def create_demo_data(db: Session) -> None:
    """Create demo organization and users for testing."""
    
    print("\n🏗️  Creating demo data...")
    
    # Create demo organization
    demo_org = Organization(
        name="Demo Company",
        slug="demo",
        timezone="UTC",
        currency="EUR",
        subscription_tier="starter",
        subscription_status="active",
        country="NL",
        legal_name="Demo Company B.V.",
    )
    db.add(demo_org)
    db.flush()
    
    # Create admin user
    admin_user = User(
        org_id=demo_org.id,
        email="admin@demo.example.com",
        password_hash=hash_password("admin123"),  # ⚠️ Change this in production!
        name="Admin User",
        role="admin",
        email_verified=True,
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(admin_user)
    db.flush()
    
    # Update org owner
    demo_org.owner_id = admin_user.id
    
    # Create demo manager user
    manager_user = User(
        org_id=demo_org.id,
        email="manager@demo.example.com",
        password_hash=hash_password("manager123"),
        name="Manager User",
        role="manager",
        email_verified=True,
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(manager_user)
    
    # Create demo regular user
    regular_user = User(
        org_id=demo_org.id,
        email="user@demo.example.com",
        password_hash=hash_password("user123"),
        name="Regular User",
        role="user",
        email_verified=True,
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(regular_user)
    
    db.commit()
    
    print(f"✅ Created demo organization: {demo_org.slug}")
    print(f"   Admin: {admin_user.email}")
    print(f"   Manager: {manager_user.email}")
    print(f"   User: {regular_user.email}")
    print(f"\n⚠️  Demo passwords are: admin123, manager123, user123")
    print(f"   Change these immediately after testing!")


def main():
    """Run migration."""
    
    print("=" * 60)
    print("🔄 JSON → PostgreSQL Data Migration")
    print("=" * 60)
    
    # Create database tables
    print("\n📊 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    db = SessionLocal()
    
    try:
        # Check if database is empty
        user_count = db.query(User).count()
        org_count = db.query(Organization).count()
        
        if user_count == 0 and org_count == 0:
            print("\n✨ Database is empty. Creating initial demo data...")
            create_demo_data(db)
        else:
            print(f"\n⚠️  Database already has {org_count} organizations and {user_count} users")
        
        # Migrate from JSON
        users_migrated = migrate_users(db)
        invoices_migrated = migrate_invoices(db)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Migration Summary")
        print("=" * 60)
        print(f"Users migrated:    {users_migrated}")
        print(f"Invoices migrated: {invoices_migrated}")
        
        # Final counts
        final_orgs = db.query(Organization).count()
        final_users = db.query(User).count()
        final_invoices = db.query(Invoice).count()
        
        print(f"\nFinal database state:")
        print(f"  Organizations: {final_orgs}")
        print(f"  Users:        {final_users}")
        print(f"  Invoices:     {final_invoices}")
        print(f"\n✅ Migration complete!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
