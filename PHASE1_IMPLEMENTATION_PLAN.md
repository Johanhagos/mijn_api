# PHASE 1: Production-Grade Architecture (Weeks 1-4)

## Overview
Transform from single-tenant, file-based storage → multi-tenant PostgreSQL with enterprise-grade security.

## Current State
- ✅ FastAPI framework ready
- ✅ JWT auth implemented
- ✅ Bcrypt password hashing
- ✅ Tax calculation engine (VAT, GST, etc.)
- ✅ Invoice system with PDF support
- ✅ Payment integrations (PayPal, Coinbase, Stripe)
- ❌ No database (JSON files only)
- ❌ No multi-tenant support
- ❌ No org isolation
- ❌ JWT fallback secret exists (security risk)
- ❌ No audit logs (database-backed)
- ❌ Invoices not immutable
- ❌ No email verification
- ❌ No password reset feature

## Architecture: Multi-Tenant Database Schema

### Core Tables

**organizations**
```
id (PK)
name
slug (unique per org)
owner_id (FK → users)
created_at
updated_at
timezone
currency
subscription_tier (starter, growth, enterprise)
subscription_status (active, suspended, canceled)
```

**users**
```
id (PK)
org_id (FK → organizations) ⭐ TENANT KEY
email (unique per org)
password_hash
name
role (admin, manager, user)
email_verified (bool)
email_verified_at
password_reset_token (for reset flow)
password_reset_expires
last_login
created_at
updated_at
```

Organization users mapping:
```
organization_users (join table)
id (PK)
organization_id (FK)
user_id (FK)
role (admin, user)
invited_by (FK → users)
joined_at
```

**invoices**
```
id (PK)
org_id (FK → organizations) ⭐ TENANT KEY
number (incremental per org, e.g. INV-2026-0001)
status (draft, finalized, paid, refunded, credited)
created_by_id (FK → users)
customer_email
customer_name
customer_country
customer_vat_id (for B2B)
amount_subtotal
amount_tax
amount_total
currency
tax_rate
tax_breakdown JSON (per line, per jurisdiction)
is_reverse_charge (bool)
finalized_at (NULL until locked)
paid_at
due_at
notes
line_items JSON (immutable after finalization)
pdf_path
created_at
updated_at
```

**invoice_line_items**
```
id (PK)
invoice_id (FK)
description
quantity
unit_price
tax_rate
tax_amount
subtotal
```

**audit_logs**
```
id (PK)
org_id (FK → organizations) ⭐ TENANT KEY
user_id (FK → users, nullable)
event_type (USER_LOGIN, INVOICE_CREATED_FINALIZED, INVOICE_PAID, etc.)
entity_type (invoice, user, payment, etc.)
entity_id
resource_org_id (org being affected)
details JSON (context)
ip_address
user_agent
created_at
```

**tokens**
```
id (PK)
user_id (FK)
token_version (for rotation)
token_hash (hashed JWT)
refresh_token_hash
is_revoked (bool)
expires_at
created_at
```

**api_keys**
```
id (PK)
org_id (FK → organizations) ⭐ TENANT KEY
name
key_hash
key_prefix (first 8 chars for display)
permissions JSON
last_used_at
created_at
```

## Implementation Stages

### Stage 1: Core Infrastructure (Days 1-3)
- [ ] Design PostgreSQL schema (done above)
- [ ] Set up SQLAlchemy ORM models
- [ ] Create Alembic migrations
- [ ] Set up database connection pool
- [ ] Environment configuration for DB_URL

### Stage 2: Migration Layer (Days 4-5)
- [ ] Create migration script: load users.json → users table
- [ ] Create migration script: load invoices.json → invoices table
- [ ] Data validation during migration
- [ ] Backup JSON files before migration

### Stage 3: Multi-Tenant Auth Layer (Days 6-8)
- [ ] Update User model with org_id
- [ ] Refactor token generation to include org_id, token_version
- [ ] Remove JWT_SECRET_KEY fallback
- [ ] Implement token versioning for rotation
- [ ] Create dependency: `Depends(get_current_org)` for org isolation
- [ ] Add @require_org_access decorator

### Stage 4: Security Hardening (Days 9-11)
- [ ] Email verification flow with token
- [ ] Password reset endpoint + token generation
- [ ] Add rate limiting (slowapi)
- [ ] Audit logging for all mutations
- [ ] Token rotation on refresh
- [ ] Remove hardcoded API keys from env defaults

### Stage 5: Invoice Compliance (Days 12-14)
- [ ] Add invoice finalization (soft lock)
- [ ] Sequential invoice numbering per org
- [ ] Immutability check on finalized invoices
- [ ] PDF generation & storage
- [ ] Credit note support (linked to original)
- [ ] Tax breakdown persistence

## Dependencies to Add
```
sqlalchemy
psycopg2-binary
python-dotenv  ✅ (already in requirements)
email-validator
slowapi (rate limiting)
python-mailgun or sendgrid (email sending)
```

## Configuration
Add to .env:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/mijn_api_db
JWT_SECRET_KEY=<strong-secret-here>  (required, no fallback)
SMTP_HOST=...
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=noreply@example.com
```

## Security Checklist
- [ ] No hardcoded secrets
- [ ] All passwords hashed (bcrypt)
- [ ] All tokens versioned & revocable
- [ ] All mutations logged to audit_logs
- [ ] Org isolation enforced at ORM level
- [ ] Rate limiting on auth endpoints
- [ ] HTTPS enforced in production
- [ ] DB backups automated
- [ ] SQL injection protected (SQLAlchemy parameterized)
- [ ] CORS properly configured

## Success Criteria (End of PHASE 1)
1. ✅ All users in PostgreSQL, auth still works
2. ✅ All invoices in PostgreSQL, with org isolation
3. ✅ Can create new org with admin user
4. ✅ Users can only see org's own data
5. ✅ All mutations logged to audit_logs
6. ✅ Email verification working
7. ✅ Password reset working
8. ✅ Token rotation on refresh
9. ✅ All invoices immutable after finalization
10. ✅ Existing API contracts unchanged (backward compatible)
