# Phase 1: Production-Grade Implementation

This document describes the Phase 1 implementation for transforming the invoice management system into a production-grade SaaS platform.

## What's Been Implemented

### 1.1 PostgreSQL Database Schema ✅

**Enhanced Models:**
- **Organizations (Shops)**: Multi-tenant root entity with business details
  - Registration numbers, EORI, contact info
  - Sequential invoice numbering per organization
  - Subscription plan tracking
  
- **Users**: Enhanced with security features
  - Email verification status
  - Token versioning for JWT invalidation
  - Last login tracking
  - Active/inactive status

- **Invoices**: Legal compliance features
  - Immutability tracking (finalized flag)
  - Finalization timestamp and user
  - Payment method and reference tracking
  - Full audit trail via invoice_history

- **Invoice Items**: VAT compliance
  - Per-line VAT breakdown
  - Subtotal, VAT amount, and total per item
  - Description field for detailed items

**New Tables:**
- `refresh_tokens`: JWT refresh token rotation
- `email_verifications`: Email verification tokens
- `password_resets`: Password reset workflow
- `subscriptions`: Stripe subscription management
- `usage_metrics`: Track invoice/API/storage usage
- `rate_limits`: Rate limiting tracking
- `invoice_history`: Immutable audit trail for invoices
- `audit_logs`: Enhanced with extra metadata

### 1.2 Multi-Tenant Architecture ✅ (Partial)

- All entities have `shop_id` (organization_id)
- Foreign key constraints enforce data relationships
- Indexes for efficient multi-tenant queries
- Sequential invoice numbering per organization

**Still TODO:**
- Enforce data isolation in API endpoints
- Organization management API endpoints
- Organization switching for users

### 1.3 Security Hardening ✅ (Partial)

**Completed:**
- Database schema for token versioning
- Refresh token rotation schema
- Email verification system
- Password reset system
- Enhanced audit logging

**Still TODO:**
- Remove JWT fallback secret from main.py
- Implement refresh token rotation in auth logic
- Add rate limiting middleware
- Add email verification workflow
- Add password reset workflow

### 1.4 Invoice Legal Safety ✅ (Partial)

**Completed:**
- Invoice immutability fields (finalized, finalized_at, finalized_by)
- Sequential numbering per organization
- VAT breakdown per line item in schema
- Invoice history tracking

**Still TODO:**
- Enforce immutability in API (prevent edits after finalization)
- Auto-finalize on send/payment
- API validation for finalized invoices

## Database Migration

### Running the Migration

1. **Set up PostgreSQL database:**
```bash
# Using Docker (recommended for development)
docker run -d \
  --name mijn-api-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=mijn_api \
  -p 5432:5432 \
  postgres:15
```

2. **Set DATABASE_URL environment variable:**
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/mijn_api"
```

3. **Run Alembic migrations:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head
```

4. **Migrate existing data from JSON files:**
```bash
python migrate_to_postgres.py
```

### Manual Migration (Alternative)

If you prefer to run SQL directly:
```bash
# Generate SQL from migration
alembic upgrade head --sql > migration.sql

# Apply to database
psql $DATABASE_URL < migration.sql
```

## Next Steps

### Phase 1 Remaining Work

1. **Update main.py to use PostgreSQL:**
   - Replace JSON file operations with SQLAlchemy queries
   - Use database sessions via `Depends(get_db)`
   - Implement data isolation per shop_id

2. **Security Implementation:**
   - Remove hardcoded JWT secret
   - Implement refresh token rotation
   - Add rate limiting middleware
   - Email verification workflow
   - Password reset workflow

3. **Invoice Immutability:**
   - Add API validation
   - Prevent edits after finalization
   - Create history snapshots on changes

### Phase 2: Monetization (Next)

1. **Subscription Billing:**
   - Stripe webhook handler
   - Plan limits enforcement
   - Subscription management API

2. **Usage Tracking:**
   - Middleware for API request counting
   - Invoice creation counting
   - Storage calculation

### Phase 3: Infrastructure (After Phase 2)

1. **Production Infrastructure:**
   - Docker production image
   - CI/CD with GitHub Actions
   - Health check endpoint

2. **Monitoring:**
   - Sentry for error tracking
   - Structured logging
   - Admin dashboard

3. **Legal:**
   - Terms of Service
   - Privacy Policy
   - GDPR compliance

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# JWT (Phase 1.3 - use strong secret)
JWT_SECRET_KEY=your-super-secret-key-min-32-chars

# Email (for verification - Phase 1.3)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Stripe (Phase 2)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Redis (for rate limiting - Phase 1.3)
REDIS_URL=redis://localhost:6379/0
```

## Testing

```bash
# Run tests
pytest tests/

# Test database connection
python -c "from database import engine; print(engine.url)"

# Test migration
python migrate_to_postgres.py
```

## Rollback Plan

If you need to rollback to JSON files:

1. Keep JSON file backups
2. Downgrade database: `alembic downgrade -1`
3. Revert code changes
4. Restart with old version

## Support

For issues or questions:
1. Check database logs: `docker logs mijn-api-postgres`
2. Check application logs
3. Verify DATABASE_URL is correct
4. Ensure PostgreSQL is running
