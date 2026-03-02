# PostgreSQL Migration Guide

## Overview
This document describes the migration from JSON file-based storage to PostgreSQL for the mijn_api FastAPI application.

## What Has Been Migrated

### ✅ Completed
1. **Database Models** (`models.py`)
   - Shop (organization/tenant)
   - User (with email, shop_id, token_version)
   - Customer
   - Invoice & InvoiceItem
   - RefreshToken
   - AuditLog
   - InvoiceHistory

2. **Database Connection** (`database.py`)
   - SessionLocal factory
   - get_db() dependency for FastAPI
   - Connection pooling

3. **Core Helper Functions** (in `main.py`)
   - `get_or_create_default_shop()` - Creates default shop
   - `get_user_by_email()` - Fetch user by email
   - `get_user_by_id()` - Fetch user by ID
   - `create_user()` - Create new user
   - `get_invoice_by_id()` - Fetch invoice
   - `get_invoices_by_shop()` - List invoices for shop
   - `create_customer()` - Create customer
   - `log_event_to_db()` - Audit logging to database

4. **Updated Endpoints**
   - `GET /users` - Lists users from database
   - `GET /users/{user_id}` - Get user from database
   - `POST /users` - Create user in database
   - `POST /register` - Register merchant with shop creation
   - `POST /login` - Login using database users
   - `async get_current_user()` - Auth dependency uses database

5. **Migration Tools**
   - `init_database.py` - Initialize database and migrate JSON data
   - `db_migration_helpers.py` - Helper functions for migration

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Database URL
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/mijn_api"
```

### 3. Initialize Database
```bash
python init_database.py
```

This will:
- Create all tables
- Create default shop
- Migrate users from users.json
- Migrate invoices from invoices.json
- Display the API key for the default shop

### 4. Start the Application
```bash
uvicorn main:app --reload
```

## Endpoints Still Using JSON (To Be Migrated)

### Invoice Endpoints
- `POST /invoices` - Create invoice (lines ~1700)
- `GET /invoices` - List invoices (lines ~1820)
- `GET /invoices/{invoice_id}` - Get invoice (lines ~2337)
- `PATCH /invoices/{invoice_id}` - Update invoice (lines ~2358)
- `POST /invoices/{invoice_id}/void` - Void invoice (lines ~1849)
- `GET /invoices/{invoice_id}/pdf` - Get PDF (lines ~3501)

### Other Endpoints
- `DELETE /users/{user_id}` - Delete user (lines ~1163)
- `GET /merchant/usage` - Usage metrics (lines ~1991)
- `POST /api-keys` - API key management (lines ~2256)
- Various debug endpoints

## Migration Pattern for Remaining Endpoints

### Example: Migrating an Invoice Endpoint

**Before (JSON-based):**
```python
@app.post("/invoices")
async def create_invoice(payload: InvoiceCreate, current_user: dict = Depends(get_current_user)):
    invoices = load_invoices()
    # ... create invoice dict ...
    invoices.append(new_invoice)
    save_invoices(invoices)
    return new_invoice
```

**After (Database-based):**
```python
@app.post("/invoices")
async def create_invoice(
    payload: InvoiceCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get shop
    shop_id = current_user["shop_id"]
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    
    # Get or create customer
    customer = db.query(Customer).filter(
        Customer.email == payload.buyer_email
    ).first()
    if not customer:
        customer = create_customer(
            db, shop_id, payload.buyer_name,
            payload.buyer_email, payload.buyer_country,
            payload.buyer_address
        )
    
    # Generate invoice number
    shop.last_invoice_number += 1
    invoice_number = f"{shop.invoice_prefix}-{shop.last_invoice_number:04d}"
    
    # Create invoice
    invoice = DBInvoice(
        shop_id=shop_id,
        customer_id=customer.id,
        invoice_number=invoice_number,
        status="DRAFT",
        issue_date=payload.issue_date or date.today(),
        due_date=payload.due_date or date.today(),
        subtotal=payload.subtotal,
        vat_total=payload.vat_amount,
        total=payload.total,
        currency=payload.currency or shop.currency
    )
    db.add(invoice)
    
    # Add line items
    for item_data in payload.items:
        item = InvoiceItem(
            invoice_id=invoice.id,
            product_name=item_data["name"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            vat_rate=item_data["vat_rate"],
            subtotal=item_data["subtotal"],
            vat_amount=item_data["vat_amount"],
            total=item_data["total"]
        )
        db.add(item)
    
    # Log to audit
    log_event_to_db(db, "INVOICE_CREATED", shop_id, current_user["email"], target=invoice.id)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice_dict_from_db(invoice)
```

## Key Differences

### 1. Multi-Tenancy
- All data is now scoped to `shop_id`
- Users belong to shops
- Always filter by `current_user["shop_id"]`

### 2. Relationships
- Use SQLAlchemy relationships: `invoice.items`, `shop.users`
- Lazy loading vs eager loading with `joinedload()`

### 3. Transactions
- Database handles atomicity automatically
- Use `db.commit()` to save changes
- Use `db.rollback()` on errors
- No need for threading locks

### 4. IDs
- UUIDs stored as strings (not integers)
- Use `str(model.id)` when returning IDs

### 5. Dates
- `issue_date` and `due_date` are `date` objects (not datetime)
- Use `.isoformat()` when serializing

## Testing

### Unit Tests
Update test fixtures to use database:
```python
@pytest.fixture
def db_session():
    from database import SessionLocal, engine
    from models import Base
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_create_invoice(db_session):
    shop = Shop(...)
    db_session.add(shop)
    db_session.commit()
    # ... test logic ...
```

## Backward Compatibility

### Legacy JSON Files
- `api_keys.json` and `sessions.json` are still used
- These can be migrated later as phase 2
- Current code checks database first, falls back to files

### Migration Script
Run anytime to sync JSON → PostgreSQL:
```bash
python init_database.py
```

## Performance Considerations

1. **Indexing**: Models have indexes on frequently queried fields
2. **Connection Pooling**: Configured in `database.py`
3. **Pagination**: Use `offset()` and `limit()` for large result sets
4. **N+1 Queries**: Use `joinedload()` to eager-load relationships

## Security

1. **SQL Injection**: Prevented by SQLAlchemy ORM
2. **Passwords**: Bcrypt hashed, stored in `password_hash`
3. **Token Version**: Supports token invalidation via `token_version`
4. **Audit Log**: All actions logged to `audit_logs` table

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/dbname
JWT_SECRET_KEY=your-secret-key-here

# Optional
SQL_ECHO=true  # Enable SQL query logging for debugging
DATA_DIR=/path/to/data  # For PDF storage
```

## Rollback Plan

If you need to rollback:
1. Restore `main.py.backup-json`
2. Keep using JSON files
3. Database remains as alternative storage

## Next Steps

1. ✅ Database models defined
2. ✅ Core helper functions created
3. ✅ User & auth endpoints migrated
4. ⏳ Migrate invoice endpoints (see pattern above)
5. ⏳ Migrate API key management
6. ⏳ Update tests
7. ⏳ Deploy to production

## Support

For issues or questions:
1. Check logs: `tail -f uvicorn.log`
2. Enable SQL logging: `export SQL_ECHO=true`
3. Review audit logs: `SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100;`
