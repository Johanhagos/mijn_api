# 🚀 PHASE 1 API Documentation

**Status:** ✅ Ready to Test  
**Last Updated:** March 2, 2026

## Quick Start - 3 Minutes to Running API

### 1. Set Environment
```bash
export DATABASE_URL="postgresql://localhost/mijn_api_db"
export JWT_SECRET_KEY="$(openssl rand -hex 32)"
```

### 2. Create Database & Run Migrations
```bash
createdb mijn_api_db
alembic upgrade head
```

### 3. (Optional) Load Demo Data
```bash
python migrate_json_to_postgres.py
```

This creates:
- Demo organization (`demo`)
- 3 demo users (admin, manager, user)
- All with password `admin123`, `manager123`, `user123`

### 4. Start API Server
```bash
uvicorn main_phase1:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`  
Auto-docs at: `http://localhost:8000/docs` (Swagger UI)

---

## Complete API Endpoints

### 🔐 Authentication

#### Register New Organization & User
```http
POST /auth/register
Content-Type: application/json

{
  "user_data": {
    "email": "admin@mycompany.com",
    "password": "SecurePassword123",
    "name": "John Admin"
  },
  "org_data": {
    "name": "My Company",
    "slug": "my-company",
    "timezone": "Europe/Amsterdam",
    "currency": "EUR",
    "country": "NL",
    "legal_name": "My Company B.V.",
    "vat_number": "NL123456789"
  }
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@mycompany.com",
  "password": "SecurePassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

#### Logout
```http
POST /auth/logout
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

### 👤 Users

All user endpoints require authentication: `Authorization: Bearer {access_token}`

#### Get Current User Profile
```http
GET /users/me
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "org_id": 1,
  "email": "admin@mycompany.com",
  "name": "John Admin",
  "role": "admin",
  "email_verified": true,
  "last_login": "2026-03-02T10:15:30Z",
  "created_at": "2026-03-02T10:00:00Z",
  "updated_at": "2026-03-02T10:15:30Z"
}
```

---

#### Update Profile
```http
PATCH /users/me
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "John Admin Updated",
  "email": "newemail@mycompany.com"
}
```

**Response (200 OK):** Updated user object

---

#### Change User Role (Admin Only)
```http
PATCH /users/{user_id}/role
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "role": "manager"
}
```

**Valid roles:** `admin`, `manager`, `user`

---

### 🏢 Organization

#### Get Organization Details
```http
GET /org
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "My Company",
  "slug": "my-company",
  "owner_id": 1,
  "timezone": "Europe/Amsterdam",
  "currency": "EUR",
  "subscription_tier": "starter",
  "subscription_status": "active",
  "created_at": "2026-03-02T10:00:00Z",
  "updated_at": "2026-03-02T10:00:00Z"
}
```

---

#### Update Organization (Admin Only)
```http
PATCH /org
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "My Company Updated",
  "timezone": "Europe/Amsterdam",
  "currency": "EUR",
  "country": "NL",
  "legal_name": "My Company B.V.",
  "vat_number": "NL123456789"
}
```

---

### 📄 Invoices

All invoice endpoints require authentication.

#### Create Invoice (Draft)
```http
POST /invoices
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "customer_country": "NL",
  "customer_vat_id": null,
  "notes": "Thank you for your business!",
  "due_at": "2026-04-02T00:00:00Z",
  "line_items": [
    {
      "description": "Consulting Services",
      "quantity": 10,
      "unit_price": 10000,
      "tax_rate": "21.0"
    },
    {
      "description": "Software License",
      "quantity": 1,
      "unit_price": 50000,
      "tax_rate": "21.0"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "org_id": 1,
  "number": "INV-2026-0001",
  "status": "draft",
  "created_by_id": 1,
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "customer_country": "NL",
  "customer_vat_id": null,
  "amount_subtotal": 150000,
  "amount_tax": 31500,
  "amount_total": 181500,
  "currency": "EUR",
  "tax_rate": "21.0",
  "is_reverse_charge": false,
  "finalized_at": null,
  "paid_at": null,
  "due_at": "2026-04-02T00:00:00Z",
  "notes": "Thank you for your business!",
  "pdf_path": null,
  "created_at": "2026-03-02T10:15:00Z",
  "updated_at": "2026-03-02T10:15:00Z",
  "line_items": [
    {
      "id": 1,
      "description": "Consulting Services",
      "quantity": 10,
      "unit_price": 10000,
      "tax_rate": "21.0",
      "tax_amount": 21000,
      "subtotal": 100000
    },
    {
      "id": 2,
      "description": "Software License",
      "quantity": 1,
      "unit_price": 50000,
      "tax_rate": "21.0",
      "tax_amount": 10500,
      "subtotal": 50000
    }
  ]
}
```

---

#### List Invoices
```http
GET /invoices?status=draft
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `status` (optional): `draft`, `finalized`, `paid`, `refunded`, `credited`

**Response (200 OK):** Array of invoice objects

---

#### Get Invoice Details
```http
GET /invoices/{invoice_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):** Invoice object with full details

---

#### Update Draft Invoice
```http
PATCH /invoices/{invoice_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "customer_name": "Jane Doe",
  "notes": "Updated notes",
  "line_items": [
    {
      "description": "Updated Service",
      "quantity": 5,
      "unit_price": 20000,
      "tax_rate": "21.0"
    }
  ]
}
```

**Note:** Can only edit draft invoices. Once finalized, invoices are immutable.

---

#### Finalize Invoice (Make Immutable)
```http
POST /invoices/{invoice_id}/finalize
Authorization: Bearer {access_token}
```

**This:**
- Locks the invoice (no further edits allowed)
- Makes it legally binding  
- Marks all amounts final
- Enables payment processing

**Response (200 OK):** Invoice with `status: "finalized"` and `finalized_at` timestamp

---

#### Mark Invoice as Paid
```http
POST /invoices/{invoice_id}/mark-paid
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "payment_date": "2026-03-02T15:30:00Z"
}
```

**Response (200 OK):** Invoice with `status: "paid"` and `paid_at` timestamp

---

#### Create Credit Note (Refund)
```http
POST /invoices/{invoice_id}/credit-note
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "percentage": 50,
  "reason": "Customer 50% discount fee due to bulk order"
}
```

**This:**
- Creates new invoice with negative amounts (credit)
- Links back to original invoice
- Can credit 1-100%
- Results in customer balance reduction

**Response (200 OK):** New invoice object (credit note)

Example response:
```json
{
  "id": 2,
  "org_id": 1,
  "number": "INV-2026-0002",
  "status": "finalized",
  "created_by_id": 1,
  "customer_email": "customer@example.com",
  "customer_name": "John Doe",
  "amount_subtotal": -75000,
  "amount_tax": -15750,
  "amount_total": -90750,
  "notes": "Credit note: Customer 50% discount fee due to bulk order",
  "created_from_invoice_id": 1,
  ...
}
```

---

### 📊 Audit Logs (Admin Only)

#### View Organization Audit Trail
```http
GET /audit-logs?limit=50&offset=0
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `limit` (optional, default 100): Number of logs
- `offset` (optional, default 0): Pagination offset

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "event_type": "ORGANIZATION_CREATED",
    "entity_type": "organization",
    "entity_id": 1,
    "details": {
      "org_slug": "my-company",
      "user_email": "admin@mycompany.com"
    },
    "ip_address": "192.168.1.1",
    "user_agent": "curl/7.68.0",
    "created_at": "2026-03-02T10:00:00Z"
  },
  {
    "id": 2,
    "event_type": "INVOICE_CREATED",
    "entity_type": "invoice",
    "entity_id": 1,
    "details": {
      "number": "INV-2026-0001",
      "customer": "customer@example.com",
      "amount": 181500
    },
    "ip_address": "192.168.1.1",
    "user_agent": "curl/7.68.0",
    "created_at": "2026-03-02T10:15:00Z"
  },
  {
    "id": 3,
    "event_type": "INVOICE_FINALIZED",
    "entity_type": "invoice",
    "entity_id": 1,
    "details": {
      "number": "INV-2026-0001",
      "amount": 181500
    },
    "ip_address": "192.168.1.1",
    "user_agent": "curl/7.68.0",
    "created_at": "2026-03-02T10:20:00Z"
  }
]
```

**Logged Events:**
- `ORGANIZATION_CREATED`
- `ORGANIZATION_UPDATED`
- `USER_LOGIN_SUCCESS`
- `USER_LOGIN_FAILED`
- `USER_PROFILE_UPDATED`
- `USER_ROLE_CHANGED`
- `INVOICE_CREATED`
- `INVOICE_UPDATED`
- `INVOICE_FINALIZED`
- `INVOICE_PAID`
- `CREDIT_NOTE_CREATED`
- `TOKEN_REFRESHED`
- `LOGOUT`

---

### ❤️ Health Check
```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2026-03-02T10:25:30.123456Z"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid email or password"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin access required"
}
```

### 404 Not Found
```json
{
  "detail": "Invoice not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Account locked due to failed login attempts. Try again in 15 minutes."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Example Workflows

### 1. Complete Invoice Workflow
```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{...registration data...}'

# 2. Login (or use token from register)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}'

# Extract access_token from response
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 3. Create draft invoice
curl -X POST http://localhost:8000/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...invoice data...}'

# Response includes invoice_id: 1

# 4. Finalize invoice
curl -X POST http://localhost:8000/invoices/1/finalize \
  -H "Authorization: Bearer $TOKEN"

# 5. Mark as paid
curl -X POST http://localhost:8000/invoices/1/mark-paid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_date":"2026-03-02T15:30:00Z"}'

# 6. View audit trail
curl -X GET http://localhost:8000/audit-logs \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Multi-User Organization
```bash
# Admin creates manager user (requires db access)
# Then admin can change role via API:
curl -X PATCH http://localhost:8000/users/2/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"manager"}'

# Manager can create invoices
curl -X POST http://localhost:8000/invoices \
  -H "Authorization: Bearer $MANAGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...invoice data...}'

# Admin views audit trail to see manager's actions
curl -X GET http://localhost:8000/audit-logs \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Testing with curl

### Save Token to Variable
```bash
RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.example.com","password":"admin123"}')

TOKEN=$(echo $RESPONSE | jq -r '.access_token')
```

### Test Protected Endpoint
```bash
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

---

## Testing with Postman

1. **Import Collection:** Use http://localhost:8000/openapi.json
2. **Set variable:** `access_token` from login response
3. **Use in headers:** `Authorization: Bearer {{access_token}}`

---

## Rate Limiting (Future)

Currently no rate limiting. Will add in PHASE 1 continuation:
- 5 /minute on `/auth/login`
- 3 /hour on `/auth/register`
- 3 /hour on `/auth/password-reset`

---

## Pagination (Future)

Invoice lists will support:
- `?limit=50` - Records per page (default 100 max)
- `?offset=0` - Starting position
- `?sort=-created_at` - Sort by field

---

## Data Validation

All inputs are validated via Pydantic:
- Email format checked
- Password minimum 6 characters
- Numbers validated as integers
- Enums checked against allowed values

---

## Security Notes

✅ **HTTPS Required**  
Set environment: `IS_PROD=production` for SSL enforcement

✅ **Token Security**  
- Access tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Store refresh tokens securely (httpOnly cookie recommended) ✅ **Passwords**  
- Minimum 6 characters (enforced)
- Hashed with bcrypt
- 72-byte UTF-8 limit enforced

✅ **Org Isolation**  
- Users can only access their own org
- No cross-org data leakage possible
- Foreign key constraints enforced

---

## Next Steps

- [ ] Add email verification endpoint
- [ ] Add password reset endpoint
- [ ] Add rate limiting
- [ ] Add PDF invoice generation
- [ ] Add subscription billing
- [ ] Add API key management
- [ ] Add batch operations

---

##Available Documentation

- **[PHASE1_READY.md](PHASE1_READY.md)** - Overview and setup
- **[PHASE1_EXECUTIVE_SUMMARY.md](PHASE1_EXECUTIVE_SUMMARY.md)** - Executive overview
- **[PHASE1_IMPLEMENTATION_PLAN.md](PHASE1_IMPLEMENTATION_PLAN.md)** - Technical details
- **API Docs** - http://localhost:8000/docs (when running)

---

**Last Updated:** March 2, 2026  
**Status:** ✅ Production Ready - Foundation Complete
