# Database Migrations & Seeding

The SQLAlchemy ORM models in `backend/app/modules/*/models.py` are the single source of truth for the MaanCamera relational and vector database schema.

## Schema Migrations (Alembic)

Apply all migrations to PostgreSQL 16 (with `pgvector` and `pg_trgm`):

```bash
cd backend
alembic upgrade head
```

## Development Seed Data

Seed deterministic `uuid5` records and real Argon2id password hashes (`hash_password()`):

```bash
cd backend
python -m app.db.seed
```
