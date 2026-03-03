# ✅ Testing Checklist - Verify Everything Works

Use this checklist to test all PHASE 1 features. Check off each item as you complete it.

---

## 🔧 Setup (Do First)

- [ ] PostgreSQL running locally
- [ ] Database created: `createdb mijn_api_dev`
- [ ] Migrations ran: `alembic upgrade head`
- [ ] Demo data loaded: `python migrate_json_to_postgres.py`
- [ ] Server started: `uvicorn main_phase1:app --reload`
- [ ] Swagger UI accessible: http://localhost:8000/docs

---

## 🔐 Authentication Tests

### Registration
- [ ] **POST /auth/register** - Can create new organization
  ```bash
  curl -X POST http://localhost:8000/auth/register \
    -H "Content-Type: application/json" \
    -d '{
      "user_data": {"email":"newtest@example.com","password":"pass123","name":"Test User"},
      "org_data": {"name":"Test Org","slug":"test-org"}
    }'
  ```
  Expected: 201 Created with tokens

- [ ] org_id created automatically
- [ ] User is marked as admin
- [ ] Password is hashed (not plaintext)
- [ ] Duplicate email rejected
- [ ] Duplicate slug rejected
- [ ] Password < 6 chars rejected
- [ ] Invalid email rejected

### Login
- [ ] **POST /auth/login** - Can login with email + password
  ```bash
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@demo.example.com","password":"admin123"}'
  ```
  Expected: 200 OK with access_token + refresh_token

- [ ] Wrong password rejected
- [ ] Non-existent email rejected  
- [ ] Token contains org_id claim
- [ ] Token contains user_id claim
- [ ] Refresh token lasts 7 days
- [ ] Access token lasts 15 minutes

### Token Refresh
- [ ] **POST /auth/refresh** - Can refresh expired token
  ```bash
  curl -X POST http://localhost:8000/auth/refresh \
    -H "Content-Type: application/json" \
    -d '{"refresh_token":"..."}'
  ```
  Expected: 200 OK with new access_token

- [ ] Old token no longer works after refresh
- [ ] Invalid refresh token rejected
- [ ] Expired refresh token rejected

### Logout
- [ ] **POST /auth/logout** - Token revocation works
  ```bash
  curl -X POST http://localhost:8000/auth/logout \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK

- [ ] Token revoked immediately
- [ ] Subsequent requests with token fail (401)

---

## 👤 User Management Tests

### Get Profile
- [ ] **GET /users/me** - Can retrieve own profile
  ```bash
  curl -X GET http://localhost:8000/users/me \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK with user data

- [ ] No password field in response
- [ ] Contains email, name, role, org_id
- [ ] Unauthenticated request fails (401)
- [ ] Expired token fails (401)

### Update Profile
- [ ] **PATCH /users/me** - Can update name
  ```bash
  curl -X PATCH http://localhost:8000/users/me \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Updated Name"}'
  ```
  Expected: 200 OK with updated data

- [ ] Email field NOT updateable (stays same)
- [ ] Role field NOT updateable (stays same)
- [ ] Password NOT updateable via this endpoint (security)

### Change User Role
- [ ] **PATCH /users/{user_id}/role** - Admin can set role
  ```bash
  curl -X PATCH http://localhost:8000/users/1/role \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"role":"manager"}'
  ```
  Expected: 200 OK

- [ ] Non-admin blocked (403)
- [ ] Can set role to: admin, manager, user
- [ ] Invalid role rejected
- [ ] Can't change other org's users

---

## 🏢 Organization Tests

### Get Organization
- [ ] **GET /org** - Can get org details
  ```bash
  curl -X GET http://localhost:8000/org \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK with org data

- [ ] Contains name, slug, created_at
- [ ] Shows correct org for authenticated user
- [ ] Different users see own orgs only

### Update Organization
- [ ] **PATCH /org** - Admin can update org
  ```bash
  curl -X PATCH http://localhost:8000/org \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"New Org Name"}'
  ```
  Expected: 200 OK

- [ ] Non-admin blocked (403)
- [ ] Slug NOT updateable (immutable)
- [ ] Name updated successfully

---

## 📄 Invoice Tests

### Create Draft Invoice
- [ ] **POST /invoices** - Can create new draft
  ```bash
  curl -X POST http://localhost:8000/invoices \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "customer_email":"john@example.com",
      "customer_name":"John Doe", 
      "customer_country":"NL",
      "line_items":[{
        "description":"Consulting",
        "quantity":10,
        "unit_price":100,
        "unit":"hours"
      }]
    }'
  ```
  Expected: 201 Created with invoice data

- [ ] Invoice number auto-generated (INV-2026-0001)
- [ ] Status set to "draft"
- [ ] Created_by is current user
- [ ] Invoice belongs to current org
- [ ] Subtotal calculated correctly
- [ ] Tax calculated (10% for NL)
- [ ] Total includes tax
- [ ] finalized_at is NULL initially
- [ ] paid_at is NULL initially

### Invoice Number Uniqueness
- [ ] Two drafts get different invoice numbers
- [ ] Invoice numbers per-org (not global)
- [ ] No gaps in numbering (sequential)

### Tax Calculation
- [ ] **NL (VAT 21%)** - Correct tax applied
  ```bash
  # Line: 100 EUR @ 10 qty = 1000 EUR
  # Tax: 1000 * 0.21 = 210 EUR
  # Total: 1210 EUR
  ```

- [ ] **DE (VAT 19%)** - Different tax applied
- [ ] **B2B (Reverse Charge)** - No tax if company number provided
- [ ] **Outside EU** - No VAT applied

### List Invoices
- [ ] **GET /invoices** - Can list own invoices
  ```bash
  curl -X GET http://localhost:8000/invoices \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK with invoice list

- [ ] Only own org's invoices shown
- [ ] Can filter by status: `?status=draft`
- [ ] Can filter by status: `?status=finalized`
- [ ] Can filter by status: `?status=paid`
- [ ] Total count returned
- [ ] Pagination works (limit, offset)

### Get Single Invoice
- [ ] **GET /invoices/{id}** - Can get invoice details
  ```bash
  curl -X GET http://localhost:8000/invoices/1 \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK with full details

- [ ] Own org invoices accessible
- [ ] Other org invoices blocked (403)
- [ ] Line items included
- [ ] Tax breakdown shown
- [ ] 404 for non-existent invoice

### Update Draft Invoice
- [ ] **PATCH /invoices/{id}** - Can edit draft
  ```bash
  curl -X PATCH http://localhost:8000/invoices/1 \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "customer_name":"Updated Name"
    }'
  ```
  Expected: 200 OK

- [ ] Draft invoices editable
- [ ] Finalized invoices NOT editable (403)
- [ ] Line items can be updated
- [ ] Customer info can be updated
- [ ] Changes reflected in totals

### Finalize Invoice
- [ ] **POST /invoices/{id}/finalize** - Lock invoice
  ```bash
  curl -X POST http://localhost:8000/invoices/1/finalize \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK with finalized_at timestamp

- [ ] Status changes to "finalized"
- [ ] finalized_at timestamp set
- [ ] Can't edit after finalize (403)
- [ ] Draft only (not already finalized)

### Mark Paid
- [ ] **POST /invoices/{id}/mark-paid** - Record payment
  ```bash
  curl -X POST http://localhost:8000/invoices/1/mark-paid \
    -H "Authorization: Bearer $TOKEN"
  ```
  Expected: 200 OK with paid_at timestamp

- [ ] Status changes to "paid"
- [ ] paid_at timestamp set
- [ ] Must be finalized first (can't pay draft)
- [ ] Can mark back to unpaid (if needed)

### Credit Note
- [ ] **POST /invoices/{id}/credit-note** - Create refund
  ```bash
  curl -X POST http://localhost:8000/invoices/1/credit-note \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"percentage":50}'
  ```
  Expected: 201 Created with credit note invoice

- [ ] New invoice created with negative amounts
- [ ] Percentage refund calculated correctly
- [ ] Linked to original invoice
- [ ] Original invoice still shows as paid
- [ ] 50% refund gives 50% deduction
- [ ] 100% refund gives full refund

---

## 📊 Audit Logging Tests

### View Audit Logs
- [ ] **GET /audit-logs** - Admin can view logs
  ```bash
  curl -X GET http://localhost:8000/audit-logs \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```
  Expected: 200 OK with audit log list

- [ ] Non-admin blocked (403)
- [ ] Shows user who made change
- [ ] Shows what changed
- [ ] Shows timestamp
- [ ] Shows IP address (if captured)

### Audit Trail Completeness
- [ ] User registration logged
- [ ] Login logged
- [ ] Invoice created logged
- [ ] Invoice finalized logged
- [ ] Invoice marked paid logged
- [ ] User role change logged
- [ ] Org update logged

---

## 🔒 Security Tests (CRITICAL)

### Multi-Tenant Isolation
- [ ] **Cross-Org Data Access BLOCKED**
  ```bash
  # Create Token for Org 1
  TOKEN_ORG1="..."
  
  # Create Token for Org 2
  TOKEN_ORG2="..."
  
  # Get invoices as Org 1
  curl -X GET http://localhost:8000/invoices -H "Authorization: Bearer $TOKEN_ORG1"
  # Returns: Org 1 invoices only
  
  # Get invoices as Org 2
  curl -X GET http://localhost:8000/invoices -H "Authorization: Bearer $TOKEN_ORG2"
  # Returns: Org 2 invoices only
  ```

- [ ] Org 1 can't see Org 2 invoices
- [ ] Org 1 can't update Org 2 invoices
- [ ] Org 1 can't list Org 2 users
- [ ] Database-level enforcement (impossible from code)

### Authentication
- [ ] Missing token rejected (401)
- [ ] Invalid token rejected (401)
- [ ] Expired token rejected (401)
- [ ] Malformed token rejected (400)

### Authorization
- [ ] Non-admin can't change roles (403)
- [ ] Non-admin can't view audit logs (403)
- [ ] Regular user can't finalize other's invoices
- [ ] Manager can create invoices
- [ ] User can view own invoices

### Data Integrity
- [ ] Can't edit finalized invoice (403)
- [ ] Can't pay draft invoice (403)
- [ ] Can't create duplicate invoice number
- [ ] Can't create invoice with invalid customer

### Rate Limiting (Not Yet Implemented)
- [ ] 5 failed login attempts → lockout
- [ ] Lockout duration: ~15 minutes
- [ ] Resets after successful login

---

## 🔌 API Contract Tests

### Response Formats
- [ ] All responses use consistent JSON format
- [ ] Error responses have message field
- [ ] Error responses have status code
- [ ] Timestamps in ISO 8601 format
- [ ] All numbers have correct decimal places

### Status Codes
- [ ] 200 OK for successful GET/PATCH
- [ ] 201 Created for successful POST (resource creation)
- [ ] 400 Bad Request for validation errors
- [ ] 401 Unauthorized for missing token
- [ ] 403 Forbidden for permission issues
- [ ] 404 Not Found for missing resources
- [ ] 500 Internal Server Error for bugs (shouldn't happen)

### Error Responses
```json
{
  "detail": "Error message here",
  "status_code": 400
}
```

- [ ] Consistent error format
- [ ] Helpful error messages
- [ ] No stack traces revealed (security)
- [ ] No internal implementation details leaked

---

## 🧮 Business Logic Tests

### Sequential Numbering
- [ ] Create invoice 1 → INV-2026-0001
- [ ] Create invoice 2 → INV-2026-0002
- [ ] Create invoice 3 → INV-2026-0003
- [ ] No gaps, always sequential

### Invoice Payoff
- [ ] Total = Subtotal + Tax
- [ ] Subtotal = SUM(quantity × unit_price × line items)
- [ ] Tax = Subtotal × tax_rate (per jurisdiction)
- [ ] Amounts match calculations

### Multi-User Workflow
- [ ] Admin creates invoice
- [ ] Manager finalizes
- [ ] User can view
- [ ] Admin marks paid
- [ ] Everyone sees updated status

---

## 🎯 End-to-End Workflow Test

Complete this workflow start to finish:

```bash
# 1. Register new organization
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"user_data":{"email":"workflow@test.com","password":"test123","name":"Test"},"org_data":{"name":"Workflow Org","slug":"workflow"}}'
# Save access_token as TOKEN

# 2. Get profile
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer $TOKEN"
# ✓ Shows correct user

# 3. Create invoice
curl -X POST http://localhost:8000/invoices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_email":"john@ex.com","customer_name":"John","customer_country":"NL","line_items":[{"description":"Work","quantity":1,"unit_price":1000}]}'
# Save invoice_id as INVOICE_ID

# 4. Get invoice
curl -X GET http://localhost:8000/invoices/$INVOICE_ID \
  -H "Authorization: Bearer $TOKEN"
# ✓ Shows correct status (draft)

# 5. Finalize invoice
curl -X POST http://localhost:8000/invoices/$INVOICE_ID/finalize \
  -H "Authorization: Bearer $TOKEN"
# ✓ Status changes to finalized

# 6. Try to edit (should fail)
curl -X PATCH http://localhost:8000/invoices/$INVOICE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_name":"Updated"}'
# ✗ Should return 403 (can't edit finalized)

# 7. Mark as paid
curl -X POST http://localhost:8000/invoices/$INVOICE_ID/mark-paid \
  -H "Authorization: Bearer $TOKEN"
# ✓ Status changes to paid

# 8. Create credit note
curl -X POST http://localhost:8000/invoices/$INVOICE_ID/credit-note \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"percentage":20}'
# ✓ Creates new invoice with -20% refund

# 9. List all invoices
curl -X GET http://localhost:8000/invoices \
  -H "Authorization: Bearer $TOKEN"
# ✓ Shows 2 invoices (original + credit note)
```

- [ ] All 9 steps complete without errors
- [ ] Totals calculated correctly
- [ ] Status progression correct
- [ ] Immutability enforced
- [ ] Multi-org isolation maintained

---

## 📈 Performance Tests

- [ ] List 100 invoices returns in < 500ms
- [ ] Update invoice returns in < 100ms
- [ ] Create invoice returns in < 200ms
- [ ] Get invoice returns in < 50ms
- [ ] No N+1 query problems
- [ ] Database connection pooling working

---

## 📋 Summary

**Total Checks:**
- Authentication: 13 tests
- Users: 8 tests
- Organization: 4 tests
- Invoices: 20 tests
- Audit: 10 tests
- Security: 12 tests
- API Contract: 10 tests
- Business Logic: 9 tests
- E2E: 1 workflow (9 steps)
- Performance: 6 tests

**= 93 Total Test Cases**

---

## ✅ Sign-Off

- [ ] All tests passed
- [ ] No errors found
- [ ] Dashboard shows all endpoints working
- [ ] Ready for next phase

**Date Tested:** __________  
**Tester:** __________  
**Result:** ✅ PASS / ❌ FAIL

---

## 🐛 Known Issues (If Any)

If you find bugs, document them here:

1. Issue: [Description]
   Status: Open / Fixed
   Fix: [Solution if fixed]

---

**You're done when all ✅ boxes are checked!**
