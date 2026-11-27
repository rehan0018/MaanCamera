# MaanCamera Production Operations Runbook

## 1. Reverse Proxy & Network Isolation
- Public ingress is terminated exclusively by Caddy (`infra/caddy/Caddyfile`) on ports `80`/`443`.
- Backend (`:8000`) and Frontend (`:3000`) use `expose:` on `maancamera_edge` with zero host port bindings.
- Postgres, Valkey, SeaweedFS, Ollama, and Prometheus operate exclusively inside `maancamera_internal` (`internal: true`).
- `/metrics` is blocked at the Caddy edge (`403 Forbidden`) and scraped internally by Prometheus (`docker compose -f docker-compose.prod.yml --profile monitoring up -d`).

## 2. Database Backup & Verified Restore Drill
1. Create a compressed PostgreSQL dump + SHA-256 checksum:
   ```bash
   POSTGRES_USER=maancamera POSTGRES_DB=maancamera_db BACKUP_DIR=/var/backups/maancamera ./infra/scripts/backup.sh
   ```
2. Run a non-destructive restore drill against an ephemeral verification database:
   ```bash
   POSTGRES_USER=maancamera ./infra/scripts/restore_verify.sh /var/backups/maancamera/maancamera_maancamera_db_<timestamp>.dump
   ```

## 3. Payment Reconciliation
- Automated task `tasks.reconcile_stale_payments` checks Razorpay `GET /v1/orders/{id}/payments` for stale `pending` orders (`> 15 min`).
- Platform admins can also trigger immediate reconciliation via `POST /api/v1/payments/admin/reconcile` or **Admin Dashboard -> Run Razorpay Reconciliation**.

## 4. Safe Rollback Procedure
1. Take a pre-deploy snapshot with `infra/scripts/backup.sh`.
2. Re-tag/roll back backend/frontend images to the previous verified digest and run `docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend`.
3. Only execute `alembic downgrade -1` if schema rollback is explicitly verified non-destructive for live transactions; otherwise restore from the pre-deploy `.dump` archive.
