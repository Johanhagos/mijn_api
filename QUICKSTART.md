# Quick Start - PostgreSQL Migration

## For Developers: Using the Migrated Code

### Setup (One-Time)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/mijn_api"
export JWT_SECRET_KEY="your-secret-key"

# 3. Initialize database (creates tables + migrates JSON data)
python init_database.py

# 4. Start server
uvicorn main:app --reload
```

### Writing New Endpoints (Database Pattern)

```python
@app.get("/my-endpoint")
async def my_endpoint(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user's shop ID
    shop_id = current_user["shop_id"]
    
    # Query database (always filter by shop_id for multi-tenancy)
    items = db.query(MyModel).filter(MyModel.shop_id == shop_id).all()
    
    # Modify data
    new_item = MyModel(shop_id=shop_id, name="test")
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Log action
    log_event_to_db(db, "ACTION_NAME", shop_id, current_user["email"])
    
    return {"items": items}
```

### Common Helper Functions

```python
# Get user by email
user = get_user_by_email(db, "user@example.com")

# Get user by ID
user = get_user_by_id(db, "uuid-string")

# Create user
user = create_user(db, email="...", password_hash="...", role="admin", shop_id="...")

# Get/create shop
shop = get_or_create_default_shop(db)

# Create customer
customer = create_customer(db, shop_id, name, email, country, address)

# Get invoice
invoice = get_invoice_by_id(db, invoice_id)

# List shop invoices
invoices = get_invoices_by_shop(db, shop_id, skip=0, limit=100)

# Log to audit
log_event_to_db(db, "USER_CREATED", shop_id, actor_email, target=user_id)
```

### Key Differences from JSON Implementation

| Old (JSON) | New (PostgreSQL) |
|------------|------------------|
| `load_users()` | `db.query(DBUser).all()` |
| `save_users(users)` | `db.commit()` |
| `with _lock:` | Not needed (DB transactions) |
| `user["id"]` (int) | `str(user.id)` (UUID) |
| Manual uniqueness checks | Database constraints |
| File I/O errors | Database exceptions |

### Testing Your Changes

```bash
# Syntax check
python -m py_compile main.py

# Run the app
uvicorn main:app --reload

# Test endpoint
curl http://localhost:8000/your-endpoint -H "Authorization: Bearer TOKEN"

# Check database
psql $DATABASE_URL -c "SELECT * FROM users;"
```

### Debugging

```bash
# Enable SQL logging (NEVER in production!)
export SQL_ECHO=true

# Check audit logs
psql $DATABASE_URL -c "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 20;"

# View server logs
tail -f uvicorn.log
```

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'psycopg2'`
```bash
pip install psycopg2-binary
```

**Issue:** `relation "users" does not exist`
```bash
python init_database.py
```

**Issue:** `current_user has no shop_id`
```python
# Ensure get_current_user() returns shop_id
# Check user was created via create_user() not old method
```

### Migration Pattern for Remaining Endpoints

**Before:**
```python
@app.post("/items")
async def create_item(item: ItemCreate, user: dict = Depends(get_current_user)):
    items = load_items()  # Load from JSON
    new_item = {"id": len(items) + 1, "name": item.name}
    items.append(new_item)
    save_items(items)  # Save to JSON
    return new_item
```

**After:**
```python
@app.post("/items")
async def create_item(
    item: ItemCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)  # Add this
):
    new_item = Item(
        shop_id=user["shop_id"],  # Always add shop_id
        name=item.name
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Log it
    log_event_to_db(db, "ITEM_CREATED", user["shop_id"], user["email"])
    
    return {"id": str(new_item.id), "name": new_item.name}
```

### Key Rules

1. **Always filter by shop_id** - Multi-tenancy requirement
2. **Use string IDs** - `str(model.id)` when returning UUIDs
3. **Add db: Session = Depends(get_db)** - Every database endpoint
4. **Commit explicitly** - `db.commit()` after changes
5. **Log important actions** - Use `log_event_to_db()`
6. **Handle exceptions** - Wrap in try/except, rollback on error

### Resources

- Full guide: `POSTGRES_MIGRATION.md`
- Implementation summary: `MIGRATION_SUMMARY.md`
- Completion report: `MIGRATION_COMPLETE.md`
- Helper functions: See `main.py` lines 530-650
- Migration utilities: `db_migration_helpers.py`

### Getting Help

1. Check existing patterns in migrated endpoints (GET /users, POST /login)
2. Review POSTGRES_MIGRATION.md for detailed examples
3. Enable SQL_ECHO to see generated queries
4. Check audit_logs table for action history
