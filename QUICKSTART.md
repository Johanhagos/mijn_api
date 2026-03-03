# 🚀 QUICK START - Get Running in 5 Minutes

## Step 1: Prerequisites (2 min)
```bash
# Check Python 3.9+
python --version

# Check PostgreSQL running
psql --version
```

## Step 2: Database Setup (1 min)
```bash
# Create database
createdb mijn_api_dev

# Run migrations
export DATABASE_URL="postgresql://localhost/mijn_api_dev"
alembic upgrade head
```

## Step 3: Load Demo Data (1 min)
```bash
# Creates demo org + 3 users
python migrate_json_to_postgres.py
```

**Demo Credentials:**
- **Admin:** admin@demo.example.com / admin123
- **Manager:** manager@demo.example.com / manager123
- **User:** user@demo.example.com / user123

## Step 4: Start Server (1 min)
```bash
export DATABASE_URL="postgresql://localhost/mijn_api_dev"
export JWT_SECRET_KEY="dev-secret-key-min-32-chars-long"
uvicorn main_phase1:app --reload --host 127.0.0.1 --port 8000
```

Server running at: http://localhost:8000

## Step 5: Test It! (Pick One)

### Option A: Browser (Easiest)
Go to: http://localhost:8000/docs (Swagger UI with "Try it out" buttons)

### Option B: Command Line
```bash
# Test 1: Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.example.com",
    "password": "admin123"
  }'

# Copy the access_token from response
TOKEN="eyJ0eXAiOiJKV1Q..."

# Test 2: Get profile
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer $TOKEN"

# Test 3: List invoices
curl -X GET http://localhost:8000/invoices \
  -H "Authorization: Bearer $TOKEN"

# Test 4: Create invoice
curl -X POST http://localhost:8000/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "john@example.com",
    "customer_name": "John Doe",
    "customer_country": "NL",
    "line_items": [
      {
        "description": "Consulting",
        "quantity": 10,
        "unit_price": 100,
        "unit": "hours"
      }
    ]
  }'
```

### Option C: Postman
Import the API endpoints from http://localhost:8000/openapi.json

---

## 📊 What You Can Do Right Now

### 1. Complete Workflow Test
```bash
# 1. Create account
POST /auth/register
{
  "user_data": {"email":"test@test.com","password":"test123","name":"Test"},
  "org_data": {"name":"My Company","slug":"myco"}
}

# 2. Login 
POST /auth/login
{"email":"test@test.com","password":"test123"}
# Save access_token

# 3. Create invoice
POST /invoices (with Bearer token)
{
  "customer_email":"customer@ex.com",
  "customer_name":"Customer",
  "customer_country":"NL",
  "line_items":[{"description":"Service","quantity":1,"unit_price":1000}]
}
# Save invoice_id

# 4. Finalize
POST /invoices/{invoice_id}/finalize (with Bearer token)

# 5. Mark paid
POST /invoices/{invoice_id}/mark-paid (with Bearer token)

# 6. Create refund
POST /invoices/{invoice_id}/credit-note (with Bearer token)
{"percentage":50}
```

### 2. Multi-Tenant Test
```bash
# Login as admin@demo
TOKEN_ADMIN="..."

# Login as user@demo
TOKEN_USER="..."

# Each can only see their org's data
GET /invoices (TOKEN_ADMIN) → Admin org invoices
GET /invoices (TOKEN_USER) → User org invoices

# Cross-org access BLOCKED (security feature)
```

### 3. Permission Test
```bash
# As regular user
PATCH /org # Fails - Not Admin

# As admin 
PATCH /org # Works

# View audit logs
GET /audit-logs # Fails - Not Admin
GET /audit-logs (admin token) # Works
```

---

## 🛠️ Troubleshooting

### Error: "Database connection failed"
```bash
# Check PostgreSQL running
psql -c "SELECT 1"

# Set DATABASE_URL correctly
export DATABASE_URL="postgresql://localhost/mijn_api_dev"
```

### Error: "JWT_SECRET_KEY not set"
```bash
# Set secret (min 32 chars)
export JWT_SECRET_KEY="your-secret-key-minimum-32-characters-long"
```

### Error: "Password hash requires 4.0+"
```bash
# Upgrade passlib
pip install --upgrade passlib
```

### Error: "Relation 'organizations' does not exist"
```bash
# Run migrations
alembic upgrade head
```

### Port 8000 already in use?
```bash
# Use different port
uvicorn main_phase1:app --reload --port 8001
```

---

## 📈 Next Steps

### To Continue Development:
1. See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for all endpoints
2. See [PHASE1_READY.md](PHASE1_READY.md) for architecture overview
3. See [PHASE1_IMPLEMENTATION_PLAN.md](PHASE1_IMPLEMENTATION_PLAN.md) for detailed specs

### To Add Features:
- Email verification: Add to [auth.py](auth.py)
- Rate limiting: Add middleware to [main_phase1.py](main_phase1.py)
- PDF generation: Use ReportLab in [invoices.py](invoices.py)

### To Deploy:
1. Push to GitHub
2. Deploy to Railway/Heroku/AWS
3. Set environment variables
4. Run `alembic upgrade head`
5. Done!

---

## 💡 Tips

- **Swagger UI** is your best friend: http://localhost:8000/docs
- **Token expires in 15 min:** Use /auth/refresh to get new one
- **All data is org-isolated:** Users can't see other orgs' data
- **Invoices are immutable:** Edit before finalize, not after
- **Audit trail captured:** Every change is logged

---

## 🎯 Success Criteria

You know it's working when:
- ✅ Login returns access_token
- ✅ GET /users/me shows your profile
- ✅ POST /invoices creates invoice
- ✅ POST /invoices/{id}/finalize locks it
- ✅ Swagger UI shows all 20+ endpoints

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | **Complete API reference** |
| [PHASE1_READY.md](PHASE1_READY.md) | How to use everything |
| [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) | What was built |
| http://localhost:8000/docs | **Interactive API explorer** |

---

**That's it! You're now running a production-grade multi-tenant SaaS platform.** 🎉

Questions? Check the docs or send a message! 💬
