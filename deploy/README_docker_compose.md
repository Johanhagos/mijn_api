Deployment with Docker Compose
==============================

This repo includes a simple Docker Compose setup to run the API, Postgres, and nginx (TLS termination).

Prerequisites
- Docker & Docker Compose installed on the host
- TLS certificates mounted into `./certs` at `/etc/letsencrypt/live/apiblockchain.io` (or update the nginx config)

Quickstart (example)

1. Copy and edit `.env.prod`, set a strong `JWT_SECRET_KEY`:

```bash
cp .env.prod .env.prod.local
# edit .env.prod.local and replace JWT_SECRET_KEY
```

2. Initialize DB schema (runs in your host Python environment or use a temporary container):

```bash
# If you have Python deps installed locally:
python scripts/init_db.py

# Or run a temporary container with the built image later and run migrations inside it.
```

3. Start the stack

```bash
docker compose up -d --build
```

4. Verify services

```bash
docker compose ps
curl -I http://127.0.0.1/health
```

Notes
- `deploy/nginx_apiblockchain.conf` expects certs under `./certs`. For testing you can mount self-signed certs or modify the nginx config to serve HTTP only.
- `Dockerfile.prod` runs `entrypoint.sh` which is expected to run migrations (see `entrypoint.sh`). Adjust as necessary for your CI/CD.
- Before calling `/create_session` in production, set `HOSTED_CHECKOUT_BASE` to `https://apiblockchain.io` (already in `.env.prod`).
