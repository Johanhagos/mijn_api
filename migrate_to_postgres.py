"""
Migration script to move data from JSON files to PostgreSQL
Run this once to migrate existing data
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import hashlib

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db_context, init_db
from models import Shop, User, Invoice, InvoiceItem, Customer, AuditLog
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def load_json_file(filename: str):
    """Load data from JSON file"""
    filepath = Path(__file__).parent / filename
    if not filepath.exists():
        print(f"Warning: {filename} not found, skipping")
        return []
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {filename} is not valid JSON, skipping")
        return []


def migrate_users(db: Session):
    """Migrate users from users.json"""
    print("Migrating users...")
    users_data = load_json_file('users.json')
    
    if not users_data:
        return {}
    
    # Create a default shop for migrated users
    default_shop = Shop(
        name="Migrated Organization",
        country="NL",
        address={"street": "Migration Street 1", "city": "Amsterdam", "postal_code": "1000AA", "country": "NL"},
        currency="EUR",
        invoice_prefix="INV",
        api_key_hash=hashlib.sha256(b"migration_key").hexdigest(),
        plan="growth"
    )
    db.add(default_shop)
    db.flush()
    
    user_mapping = {}  # old name -> new id
    
    for user_data in users_data:
        user = User(
            shop_id=default_shop.id,
            email=user_data.get('email', f"{user_data['name']}@migrated.local"),
            password_hash=user_data.get('password', ''),
            role=user_data.get('role', 'user'),
            name=user_data.get('name'),
            active=True,
            email_verified=False,
            token_version=1
        )
        db.add(user)
        db.flush()
        user_mapping[user_data.get('name')] = user.id
        print(f"  Migrated user: {user.name} ({user.email})")
    
    return user_mapping, default_shop.id


def migrate_invoices(db: Session, shop_id: str):
    """Migrate invoices from invoices.json"""
    print("Migrating invoices...")
    invoices_data = load_json_file('invoices.json')
    
    if not invoices_data:
        return
    
    for invoice_data in invoices_data:
        # Create customer if not exists
        buyer = invoice_data.get('buyer', {})
        customer = Customer(
            shop_id=shop_id,
            name=buyer.get('name', 'Unknown'),
            email=buyer.get('email'),
            vat_number=buyer.get('vat_number'),
            address=buyer.get('address', {}),
            country=buyer.get('country', 'NL')
        )
        db.add(customer)
        db.flush()
        
        # Create invoice
        invoice = Invoice(
            shop_id=shop_id,
            customer_id=customer.id,
            invoice_number=invoice_data.get('invoice_number', 'MIGRATED-001'),
            status=invoice_data.get('status', 'DRAFT').upper(),
            issue_date=datetime.fromisoformat(invoice_data['issue_date']) if 'issue_date' in invoice_data else datetime.now(),
            due_date=datetime.fromisoformat(invoice_data['due_date']) if 'due_date' in invoice_data else datetime.now(),
            subtotal=invoice_data.get('subtotal', 0),
            vat_total=invoice_data.get('vat_total', 0),
            total=invoice_data.get('total', 0),
            currency=invoice_data.get('currency', 'EUR'),
            finalized=invoice_data.get('status') in ['SENT', 'PAID'],
            payment_method=invoice_data.get('payment_system'),
            payment_reference=invoice_data.get('stripe_payment_id') or invoice_data.get('blockchain_tx_id')
        )
        db.add(invoice)
        db.flush()
        
        # Create invoice items
        for item_data in invoice_data.get('items', []):
            quantity = item_data.get('quantity', 1)
            unit_price = item_data.get('unit_price', 0)
            vat_rate = item_data.get('vat_rate', 0)
            subtotal = quantity * unit_price
            vat_amount = subtotal * (vat_rate / 100)
            
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_name=item_data.get('description', 'Item'),
                description=item_data.get('description'),
                quantity=quantity,
                unit_price=unit_price,
                vat_rate=vat_rate,
                subtotal=subtotal,
                vat_amount=vat_amount,
                total=subtotal + vat_amount
            )
            db.add(item)
        
        print(f"  Migrated invoice: {invoice.invoice_number}")


def main():
    """Run the migration"""
    print("=" * 60)
    print("Starting migration from JSON to PostgreSQL")
    print("=" * 60)
    
    # Initialize database (create tables)
    print("\nInitializing database...")
    init_db()
    print("Database initialized")
    
    # Migrate data
    with get_db_context() as db:
        try:
            user_mapping, shop_id = migrate_users(db)
            migrate_invoices(db, shop_id)
            
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Backup your JSON files (users.json, invoices.json)")
            print("2. Update your .env file with DATABASE_URL")
            print("3. Restart your application")
            print("4. Test the application with PostgreSQL")
            
        except Exception as e:
            print(f"\nError during migration: {e}")
            raise


if __name__ == "__main__":
    main()
