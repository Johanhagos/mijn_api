# 🗺️ Visual Guide - How Everything Fits Together

This document shows how all the components work together.

---

## 🏗️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Your Browser                          │
│  http://localhost:8000/docs (Swagger UI)               │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP Requests
                         │
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI App                            │
│                 main_phase1.py                           │
│                                                           │
│  ┌─── 20 REST Endpoints ───┐                            │
│  │ • /auth/register        │                            │
│  │ • /auth/login           │                            │
│  │ • /users/me             │                            │
│  │ • /invoices             │                            │
│  │ • /org                  │                            │
│  │ • /audit-logs           │                            │
│  └─────────────────────────┘                            │
│                                                           │
│  Dependency Injection:                                   │
│  • get_current_user() → Extract JWT token              │
│  • get_db() → Database session                          │
│  • require_admin() → Admin enforcement                  │
└────────────────────────┬────────────────────────────────┘
                         │ ORM Queries
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ models.py    │ │ invoices.py  │ │ auth.py      │
│              │ │              │ │              │
│ • Org        │ │ • Create     │ │ • JWT tokens │
│ • User       │ │ • Finalize   │ │ • Passwords  │
│ • Invoice    │ │ • Tax calc   │ │ • Brute force│
│ • LineItem   │ │ • Credit     │ │ • Audit log  │
│ • AuditLog   │ │   notes      │ │ • Versioning│
│ • Token      │ │ • Number gen │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │ SQL
                         │
┌────────────────────────▼────────────────────────────────┐
│                  PostgreSQL Database                     │
│                    (db.py config)                        │
│                                                           │
│  ┌──────────────────────────────────────────────┐       │
│  │ organizations table (companies)              │       │
│  │ ├─ users table (team members)                │       │
│  │ │  └─ token_versions (security)              │       │
│  │ │  └─ api_keys (for future)                  │       │
│  │ ├─ invoices table (documents)                │       │
│  │ │  └─ invoice_line_items (details)           │       │
│  │ └─ audit_logs table (compliance)             │       │
│  └──────────────────────────────────────────────┘       │
│                                                           │
│  Alembic Migrations (001_initial_schema.py)             │
│  • CREATE TABLE statements                              │
│  • Foreign keys                                         │
│  • Indexes & constraints                                │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                   Data Migration                        │
│            migrate_json_to_postgres.py                  │
│                                                          │
│  users.json ──────┐                                     │
│  invoices.json ───┤──→ PostgreSQL                       │
│  (optional)       │     (creates demo if empty)         │
│                   └──→ Demo: 1 org, 3 users             │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│               Validation & Schemas                      │
│                schemas.py (40+ models)                  │
│                                                          │
│  LoginRequest ──→ validate ──→ LoginResponse            │
│  InvoiceCreate → validate → InvoiceResponse             │
│  UserUpdate ──→ validate ──→ UserResponse               │
└────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Example: Create Invoice

```
1. USER ACTION
   └─ Click "Create Invoice" in app
   └ POST /invoices with invoice data

2. API REQUEST VALIDATION
   └─ main_phase1.py receives request
   └─ Pydantic validates against InvoiceCreateRequest (schemas.py)
   └─ Extract JWT token via get_current_user() (auth.py)
   └─ Verify JWT signature & expiry (auth.py)
   └─ Lookup User in database (models_phase1.py)

3. AUTHORIZATION CHECK
   └─ Verify user has Bearer token
   └─ Verify user hasn't exceeded limits
   └─ Verify invoice belongs to user's org

4. BUSINESS LOGIC
   └─ invoices.py handles:
      ├─ Generate sequential number (INV-2026-0001)
      ├─ Calculate subtotal from line items
      ├─ Determine tax rate by country (schemas/config)
      ├─ Calculate tax amount
      ├─ Calculate total (subtotal + tax)
      └─ Create structured invoice object

5. DATABASE INSERTION
   └─ models_phase1.py handles:
      ├─ Insert Invoice row
      ├─ Insert InvoiceLineItem rows
      ├─ Set org_id = user.org_id (isolation)
      └─ Create AuditLog entry

6. RESPONSE GENERATION
   └─ Format as InvoiceResponse (schemas.py)
   └─ Return JSON with:
      ├─ id
      ├─ invoice number
      ├─ status = "draft"
      ├─ amounts (subtotal, tax, total)
      ├─ line items
      └─ timestamps

7. SECURITY
   └─ Audit log created (auth.py)
      ├─ User: extracted from JWT
      ├─ Action: "invoice_created"
      ├─ Timestamp: now
      └─ Fields: invoice details
```

---

## 🔐 Multi-Tenant Isolation Example

```
Scenario: Admin_OrgA tries to access Invoice from OrgB

1. Admin logs in to OrgA
   POST /auth/login
   ├─ Validates credentials
   ├─ Creates JWT with claims:
   │  ├─ sub: admin_id
   │  ├─ org_id: A
   │  └─ exp: +15 minutes
   └─ Returns access_token

2. Admin tries to get Invoice from OrgB
   GET /invoices/99
   Header: Authorization: Bearer <token>

3. FastAPI Handler
   @app.get("/invoices/{invoice_id}")
   async def get_invoice(
      invoice_id: int,
      user: User = Depends(get_current_user),  ← Extracts User with org_id=A
      db = Depends(get_db)
   ):
      invoice = db.query(Invoice).filter(
         Invoice.id == invoice_id,
         Invoice.org_id == user.org_id  ← CRITICAL: Checks org_id
      ).first()

4. Query Result
   ├─ Invoice 99 has org_id = B
   ├─ user.org_id = A
   ├─ A ≠ B → Query returns None
   └─ Handler returns 404 (Not Found)

5. Security Outcome
   ├─ Admin_OrgA never sees Invoice from OrgB
   ├─ No error message reveals OrgB's data
   ├─ Logged in audit_log (attempt recorded)
   └─ ZERO chance of cross-org data leak
```

---

## 📝 Invoice Status Flow

```
Draft Invoice (Editable)
    │
    ├─ User: Can edit customer, line items, amounts
    ├─ Manager: Can review
    └─ Admin: Can review, finalize, or delete
    │
    ▼
Finalize Invoice (Immutable)
    │
    ├─ API call: POST /invoices/{id}/finalize
    ├─ Status changes: draft → finalized
    ├─ Timestamp: finalized_at = now
    └─ Immutability enforced: Can't edit, can't patch
    │
    ▼
Mark Paid
    │
    ├─ API call: POST /invoices/{id}/mark-paid
    ├─ Status changes: finalized → paid
    ├─ Timestamp: paid_at = now
    └─ Still immutable: Can't undo payment
    │
    ├─ Option A: Create Credit Note (Partial Refund)
    │  ├─ POST /invoices/{id}/credit-note
    │  ├─ Create new invoice with negative amounts
    │  ├─ Original invoice remains "paid"
    │  └─ Refund tracked separately
    │
    └─ Option B: Create Credit Note (Full Refund)
       ├─ POST /invoices/{id}/credit-note
       ├─ Percentage: 100
       ├─ New invoice: (-subtotal), (-tax), (-total)
       └─ Effectively reverses the invoice
```

---

## 🔑 Authentication Token Flow

```
1. USER REGISTERS
   POST /auth/register
   ├─ Request: email, password, name, org_data
   ├─ validation: schemas.py validates
   ├─ Password hashing: auth.py.hash_password()
   │  └─ Uses bcrypt with 72-byte limit
   ├─ Database insert: User + Organization
   └─ Response: access_token + refresh_token

2. USER LOGS IN
   POST /auth/login  
   ├─ Request: email, password
   ├─ Lookup: User by email
   ├─ Verify: auth.verify_password()
   │  └─ Compare bcrypt hashes, NOT plaintext
   ├─ Create tokens: auth.create_access_token()
   │  ├─ Access token (15 min expiry)
   │  │  ├─ sub: user_id
   │  │  ├─ org_id: user_org_id
   │  │  └─ exp: now + 15min
   │  └─ Refresh token (7 day expiry)
   │     └─ Can be used to get new access token
   ├─ Audit log: "user_login" recorded
   └─ Response: {access_token, refresh_token, user}

3. USER MAKES API REQUEST
   GET /invoices
   Header: Authorization: Bearer eyJ0eXA...

4. FASTAPI HANDLER
   @app.get("/invoices")
   async def list_invoices(
      user = Depends(get_current_user)  ← Dependency
   ):
      # Below happens automatically:
      │ 1. Extract token from header
      │ 2. Verify JWT signature (using JWT_SECRET_KEY)
      │ 3. Check token not expired (exp claim)
      │ 4. Lookup User in database by user_id
      │ 5. Return User object with org_id
      │
      return invoices for user.org_id

5. TOKEN REFRESH (When Access Token Expiring)
   POST /auth/refresh
   ├─ Request: refresh_token
   ├─ Validate: Token still valid (< 7 days old)
   ├─ Create: New access_token (15 min)
   └─ Response: {access_token}

6. LOGOUT
   POST /auth/logout
   ├─ Request: Authorization header
   ├─ Action: Invalidate token (mark as revoked)
   │  └─ Uses token_versions table to track
   └─ Result: Subsequent requests with old token → 401 Unauthorized
```

---

## 🗂️ File Dependencies

```
main_phase1.py (FastAPI app)
    ├─ Imports: models_phase1
    │   └─ Defines User, Invoice, Organization, etc
    │
    ├─ Imports: auth
    │   ├─ get_current_user() dependency
    │   ├─ require_admin() dependency
    │   └─ Password/token functions
    │
    ├─ Imports: schemas
    │   ├─ Request validation (Pydantic)
    │   └─ Response formatting
    │
    ├─ Imports: db
    │   ├─ get_db() dependency
    │   └─ PostgreSQL connection
    │
    └─ Imports: invoices
        ├─ create_draft_invoice()
        ├─ finalize_invoice()
        └─ generate_invoice_number()

models_phase1.py (ORM)
    ├─ Imports: db
    │   └─ Base class, engine, session
    │
    └─ Defines: 7 table models
        ├─ Organization
        ├─ User
        ├─ Invoice
        ├─ InvoiceLineItem
        ├─ AuditLog
        ├─ TokenVersion
        └─ APIKey

auth.py (Security)
    ├─ Imports: models_phase1
    │   └─ To lookup User objects
    │
    ├─ Imports: db
    │   └─ Database sessions
    │
    └─ Provides:
        ├─ JWT creation/verification
        ├─ Password hashing
        ├─ Token rotation
        └─ Brute force protection

invoices.py (Business Logic)
    ├─ Imports: models_phase1
    │   └─ Invoice, LineItem objects
    │
    ├─ Imports: auth
    │   └─ AuditLog creation
    │
    └─ Provides:
        ├─ Invoice creation
        ├─ Tax calculations
        ├─ Number generation
        └─ Credit note logic

schemas.py (Validation)
    └─ Standalone Pydantic models
        ├─ Request validation
        └─ Response formatting

db.py (Configuration)
    ├─ PostgreSQL connection string
    ├─ SQLAlchemy engine
    └─ Session maker

migrate_json_to_postgres.py (Data)
    ├─ Imports: models_phase1
    ├─ Imports: db
    └─ Loads: users.json, invoices.json
```

---

## 🧪 Testing Flow

```
Start: python -m pytest (if using pytest)
or
Swagger UI: http://localhost:8000/docs
or
Manual testing: curl commands

Example Test: "Create and Finalize Invoice"

┌─ Prepare
│  ├─ Get token: POST /auth/login
│  └─ Save: TOKEN, USER_ID
│
├─ Create Draft
│  ├─ POST /invoices
│  ├─ Response: invoice_id, status="draft"
│  └─ Save: INVOICE_ID
│
├─ Verify Can Edit
│  ├─ PATCH /invoices/{INVOICE_ID}
│  ├─ Change customer name
│  └─ Expected: 200 OK
│
├─ Finalize
│  ├─ POST /invoices/{INVOICE_ID}/finalize
│  ├─ Response: finalized_at timestamp
│  └─ Status: "finalized"
│
├─ Verify Can't Edit
│  ├─ PATCH /invoices/{INVOICE_ID}
│  ├─ Try to change customer
│  └─ Expected: 403 Forbidden
│
├─ Mark Paid
│  ├─ POST /invoices/{INVOICE_ID}/mark-paid
│  └─ Response: paid_at timestamp
│
└─ Create Credit Note
   ├─ POST /invoices/{INVOICE_ID}/credit-note
   ├─ percentage: 50
   └─ Response: new invoice_id (with negative amounts)

Result: ✅ All tests pass
```

---

## 🚀 Deployment Architecture

```
Development
│
├─ main_phase1.py
├─ models_phase1.py
├─ auth.py, invoices.py
├─ schemas.py, db.py
└─ Database: PostgreSQL localhost

         Run locally:
         uvicorn main_phase1:app --reload


Production (Railway/AWS/Heroku)
│
├─ Docker Container (from Dockerfile)
│  ├─ Python 3.11
│  ├─ All code
│  └─ requirements.txt installed
│
├─ Environment Variables (Secrets)
│  ├─ DATABASE_URL=postgresql://...
│  └─ JWT_SECRET_KEY=<random>
│
├─ Alembic Migrations
│  └─ alembic upgrade head
│
├─ CloudDB PostgreSQL
│  └─ AWS RDS / Railway PostgreSQL
│
└─ Load Balancer / API Gateway
   └─ Distributes requests to app instances


Scale
│
├─ 100 users: 1 app instance ✅
├─ 1,000 users: 2-3 app instances + load balancer
├─ 10,000 users: PostgreSQL read replicas
└─ 100,000+ users: Microservices
```

---

## 📚 Documentation Map

```
START_HERE.md (You are here)
│
├─ QUICKSTART.md
│  ├─ 5 min setup
│  └─ Demo credentials
│
├─ API_DOCUMENTATION.md
│  ├─ 20 endpoints
│  ├─ curl examples
│  └─ Workflows
│
├─ INDEX.md
│  ├─ File navigation
│  └─ Where to look for...
│
├─ TESTING_CHECKLIST.md
│  └─ 93 test cases
│
├─ DELIVERY_SUMMARY.md
│  ├─ Features overview
│  ├─ Security checklist
│  └─ Deployment guide
│
├─ NEXT_STEPS.md
│  ├─ Email verification
│  ├─ Payment processing
│  ├─ Web dashboard
│  └─ Timeline to PHASE 2
│
├─ PHASE1_IMPLEMENTATION_PLAN.md
│  ├─ Deep architecture
│  ├─ Database design
│  └─ Security model
│
└─ PHASE1_READY.md
   ├─ How to use components
   └─ Modification guide
```

---

## ✨ Key Insights

### Why This Architecture?

1. **Multi-Tenant** - Each organization is isolated, can scale independently
2. **Immutable Finance Records** - Can't edit invoices after finalization (legal requirement)
3. **Audit Trail** - Every change logged for compliance
4. **Role-Based Access** - Admin/manager/user permissions enforced
5. **Type Safety** - Pydantic + type hints catch errors early
6. **PostgreSQL** - ACID compliance for financial data

### Why These Tools?

- **FastAPI** - Modern, fast, auto-documentation
- **PostgreSQL** - Reliable, scalable, perfect for structured data
- **SQLAlchemy** - Prevents SQL injection, clean code
- **JWT Tokens** - Stateless auth (no session storage)
- **Pydantic** - Validates all inputs automatically
- **Alembic** - Version control for database schema

### What's Missing? (Not included yet)

- Email verification (coming PHASE 1 continuation)
- Password reset (coming PHASE 1 continuation)
- Rate limiting (coming PHASE 1 continuation)
- PDF generation (coming PHASE 1 continuation)
- Web dashboard (coming PHASE 2)
- Payment processing (coming PHASE 2)

---

## 🎓 Learning Resources

Each file teaches you something:

- **main_phase1.py** - FastAPI patterns
- **models_phase1.py** - SQLAlchemy ORM
- **auth.py** - JWT tokens & security
- **invoices.py** - Business logic complexity
- **schemas.py** - Pydantic validation
- **PHASE1_IMPLEMENTATION_PLAN.md** - Architecture thinking

---

## 🎯 Next Steps

1. **Run it** - Follow [QUICKSTART.md](QUICKSTART.md)
2. **Test it** - Use [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
3. **Understand it** - Read [PHASE1_IMPLEMENTATION_PLAN.md](PHASE1_IMPLEMENTATION_PLAN.md)
4. **Extend it** - Pick a feature from [NEXT_STEPS.md](NEXT_STEPS.md)
5. **Deploy it** - Follow [DELIVERY_SUMMARY.md](DELIVERY_SUMMARY.md#-deployment-ready)

---

**Everything is connected, documented, and ready to use.** Start with [QUICKSTART.md](QUICKSTART.md) and you'll be live in 5 minutes.

Good luck! 🚀
