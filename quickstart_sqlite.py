#!/usr/bin/env python3
"""
Quick SQLite Setup - Get running immediately without PostgreSQL
This creates demo data using SQLite database instead of PostgreSQL
"""

import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_phase1 import Base, Organization, User, Invoice, InvoiceLineItem, AuditLog
from auth import hash_password, create_access_token
from invoices import calculate_invoice_amounts

# Use SQLite for quick testing
DATABASE_URL = "sqlite:///./mijn_api_dev.db"
print("Using SQLite database for quick testing")
print(f"📦 Database: {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all tables"""
    print("📊 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")


def create_demo_data():
    """Create demo organization and users"""
    db = SessionLocal()
    try:
        # Check if demo data already exists
        demo_org = db.query(Organization).filter(Organization.slug == "demo").first()
        if demo_org:
            print("⏭️  Demo data already exists, skipping creation")
            return
        
        # Solution to circular dependency: create org with temp owner_id=1, then fix it
        print("🏢 Creating demo organization (with admin owner)...")
        
        # First, create organization with a placeholder owner_id (will be updated)
        org = Organization(
            name="Demo Organization",
            slug="demo",
            owner_id=1,  # Placeholder - will update after user created
            timezone="UTC",
            currency="EUR",
            subscription_tier="starter",
            subscription_status="active",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(org)
        db.flush()
        org_id = org.id
        
        print("👥 Creating demo admin user...")
        
        # Create admin user with the org
        admin_user = User(
            org_id=org_id,
            email="admin@demo.example.com",
            password_hash=hash_password("admin123"),
            name="Admin User",
            role="admin",
            email_verified=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(admin_user)
        db.flush()
        admin_id = admin_user.id
        print(f"  ✅ admin@demo.example.com / admin123")
        
        # Now update org to point to the real admin user
        org.owner_id = admin_id
        
        # Create other demo users
        demo_users = [
            {
                "email": "manager@demo.example.com",
                "password": "manager123",
                "name": "Manager User",
                "role": "manager"
            },
            {
                "email": "user@demo.example.com",
                "password": "user123",
                "name": "Regular User",
                "role": "user"
            }
        ]
        
        print("👥 Creating additional demo users...")
        for user_data in demo_users:
            user = User(
                org_id=org_id,
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                name=user_data["name"],
                role=user_data["role"],
                email_verified=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(user)
            print(f"  ✅ {user_data['email']} / {user_data['password']}")
        
        # Create sample invoice
        print("📄 Creating sample invoice...")
        admin_user = db.query(User).filter(
            User.email == "admin@demo.example.com",
            User.org_id == org_id
        ).first()
        
        # Amount in cents: 1000.00 EUR = 100000 cents
        invoice = Invoice(
            org_id=org_id,
            number="INV-2026-0001",
            status="draft",
            created_by_id=admin_user.id,
            customer_email="customer@example.com",
            customer_name="Sample Customer",
            customer_country="NL",
            customer_vat_id=None,
            amount_subtotal=100000,  # 1000.00 EUR in cents
            amount_tax=21000,        # 210.00 EUR (21% VAT)
            amount_total=121000,     # 1210.00 EUR
            currency="EUR",
            tax_rate="21.0",
            is_reverse_charge=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(invoice)
        db.flush()
        
        # Add line items
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description="Professional Services",
            quantity=10,
            unit_price=10000,  # 100.00 EUR in cents
            tax_rate="21.0",
            tax_amount=21000,  # 210.00 EUR in cents
            subtotal=100000    # 1000.00 EUR in cents
        )
        db.add(line_item)
        
        db.commit()
        print("✅ Demo data created successfully!")
        print("")
        print("🎉 You're all set! Demo organization and users created.")
        print("")
        print("Demo Credentials:")
        print("  Admin:   admin@demo.example.com / admin123")
        print("  Manager: manager@demo.example.com / manager123")
        print("  User:    user@demo.example.com / user123")
        print("")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


def main():
    """Main function"""
    print("")
    print("=" * 60)
    print("🚀 Quick Setup with SQLite (Testing)")
    print("=" * 60)
    print("")
    
    try:
        create_tables()
        create_demo_data()
        print("")
        print("✨ Setup complete! Run: uvicorn main_phase1:app --reload")
        print("📚 Then visit: http://localhost:8000/docs")
        return 0
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
